-- 10_data_quality_checks.sql
-- Run after every load. The expected result is in each comment.
-- In a clean production pipeline most of these would be 0; this dataset has known issues planted.

use role sysadmin;
use warehouse practice_wh;

-- 1. Row counts per raw table
select table_name, row_count
from claims_db.information_schema.tables
where table_schema = 'RAW' and table_type = 'BASE TABLE'
order by table_name;

-- 2. Claim IDs duplicated in RAW (expected: 12)
select count(*) as dup_claim_ids
from (select claim_id from claims_db.raw.claims group by claim_id having count(*) > 1);

-- 3. Service date after received date (expected: 3)
select count_if(is_bad_service_date) as bad_service_dates
from claims_db.staging.stg_claims;

-- 4. Overlapping eligibility spans (expected: 25)
select count(*) as overlapping_pairs
from claims_db.staging.stg_eligibility a,
     claims_db.staging.stg_eligibility b
where a.member_id       = b.member_id
  and a.eligibility_id  < b.eligibility_id
  and a.effective_date <= b.term_date
  and b.effective_date <= a.term_date
  and a.is_valid_span
  and b.is_valid_span;

-- 5. Paid claims with no eligibility (expected: 45)
select count_if(is_no_eligibility) as paid_no_eligibility
from claims_db.marts.paid_claims;

-- 6. Mart reconciles to staging (expected: both 23,299,313.41)
select (select sum(total_paid_amt) from claims_db.staging.stg_claims where is_paid_claim) as staging_paid,
       (select sum(total_paid_amt) from claims_db.marts.paid_claims)                     as mart_paid;