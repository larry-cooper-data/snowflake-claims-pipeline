# Data dictionary

This is a fake medical claims extract from a TPA that runs self-funded health plans for 30 employer groups. Everything in it is made up: the people, employers, providers, NPIs and dollar amounts.

- **Service dates:** claims start between 2025-01-01 and 2026-09-30. A few hospital stays that start late in September run into early October.
- **Extract date:** 2026-10-15. Contains every claim received through 2026-10-14.
- **Size:** about 8,600 members, 69,000 claims and 109,000 claim lines
- **Scope:** medical claims only, no pharmacy claims. Allowed cost runs about $237 per member per month, lower than a full plan with drugs.

The data has realistic quality problems built in on purpose (duplicates, bad dates, overlapping eligibility and more) so the pipeline has real issues to catch.

## Files

| File | Rows | One row per |
|---|---|---|
| claims.csv | 69,206 | claim (header) |
| claim_lines.csv | 108,612 | claim line |
| members.csv | 8,592 | person covered |
| eligibility.csv | 8,993 | coverage span (member + plan + date range) |
| providers.csv | 376 | doctor, therapist, hospital, surgery center, lab or imaging center |
| employer_groups.csv | 30 | employer |
| plans.csv | 4 | benefit plan |
| fee_schedule.csv | 130 | in-network professional rate per procedure per year |
| procedure_codes.csv | 65 | CPT/HCPCS code |
| revenue_codes.csv | 19 | facility revenue code |
| diagnosis_codes.csv | 53 | ICD-10 code |
| denial_reasons.csv | 8 | denial code |
| place_of_service.csv | 7 | place of service code |
| claim_status_codes.csv | 5 | claim status |

Descriptions of procedure codes are plain English, not the official CPT wording.

## How the tables connect

```
employer_groups ─< eligibility >─ members ─< claims ─< claim_lines >─ procedure_codes
                       │                       │  │                 └─ revenue_codes
                     plans                     │  └─ dx_code_1..4 ─ diagnosis_codes
                                               └─ billing_provider_id / rendering_provider_id ─ providers
```

- **The group is not on the claim.** To get it, join the claim to `eligibility` where the service date falls inside the span: `service_from_date BETWEEN effective_date AND term_date`.
- **The subscriber** is `members.subscriber_id`, which is the subscriber's own member_id. Use it to roll a family up.
- A claim's lines join on `claim_id`.

## Claims

| Column | Notes |
|---|---|
| claim_type | `PROF` = professional (CMS-1500: doctors, labs, imaging centers). `INST` = institutional (UB-04: hospitals and surgery centers). |
| bill_type | INST only. `0111` inpatient, `0131` hospital outpatient (ER, outpatient surgery, imaging, labs, infusions), `0831` surgery center. |
| place_of_service | PROF only. See place_of_service.csv. |
| admit_date, discharge_date | Inpatient claims only. |
| network_status | Network status of the billing provider: INN or OON. |
| claim_status | `P` paid, `D` denied, `H` pended, `X` reversed, `A` adjustment. See below. |
| original_claim_id | On an `A` claim, the claim it replaced. |
| dx_code_1 to dx_code_4 | dx_code_1 is the primary diagnosis. |
| total_* amounts | Sums of the lines. allowed = paid + deductible + copay + coinsurance. |

**Claim status rules**
- **Money paid = claims with status P or A.** An X claim underpaid one line by mistake. It was reversed and replaced by an A claim with the correct amount (`original_claim_id` points back to it). Counting both double counts.
- **H (pended)** claims are received but not finalized. Their allowed, paid and member-share amounts are NULL, and processed_date is NULL.
- **D (denied)** claims carry a header `denial_reason_code`, and all their amounts are 0.
- **Individual lines can be denied** (`D07` bundled) while the rest of the claim pays.
- **Paid dates** fall on Tuesdays and Fridays (payment runs).

## Eligibility

Each row is a coverage span: member, group, plan, tier (EE, ES, EC, FAM) and date range. A member can have several rows if they changed plans or left and came back. Dependents are covered from their birth date at the earliest, and their spans end the month they turn 26.

**Open-ended spans are stored two ways:** term_date `9999-12-31` (older loads) or blank/NULL (newer loads). Handle both.

## How claims were priced and paid

- **In-network professional:** fee_schedule rate for the service-date year, times units, capped at billed. Modifier 26 (the radiologist's read only) pays 32% of the rate. 2026 rates are 3% above 2025.
- **Out-of-network professional:** 140% of the fee schedule, capped at billed.
- **In-network facility:** billed times the facility's `contract_pct_of_billed` (in providers).
- **Out-of-network facility:** 40% of billed.

**Member cost share** follows plans.csv:
- **In-network preventive and immunizations:** paid at 100%. That includes screening colonoscopies with diagnosis Z12.11.
- **Office visits, psychotherapy and PT evaluations:** one copay per claim (PCP or specialist), except on the HDHP. PT treatment sessions go to deductible and coinsurance.
- **ER facility claims:** the ER copay covers the visit, except on the HDHP.
- **Everything else:** deductible first, then coinsurance (higher out of network).
- **Out-of-pocket max:** deductible, copays and coinsurance all count toward it. Once it's met, the member pays $0.
- **Accumulators:** per member, per calendar year of the service date. Family deductibles aren't modeled.
- **Emergency care out of network** pays at in-network cost share.
- **The EPO** denies out-of-network non-emergency claims (D08).

## Loading notes

- Comma-delimited with a header row. Text with commas is in double quotes (provider names).
- Dates are `YYYY-MM-DD`. Money has 2 decimals. Blank means NULL.
- Load IDs, NPIs, ZIP codes and all codes as text. Several have leading zeros.
- `sql/01_create_raw_tables.sql` creates all 14 raw tables in `CLAIMS_DB.RAW`.

## Rebuilding the data

From the repo folder:

```
python3 generator/generate_claims_data.py data
```

It uses a fixed seed, so you get the exact same files every time.
