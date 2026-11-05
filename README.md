# Healthcare Claims Data Pipeline on Snowflake

A layered Snowflake pipeline for medical claims data: raw files are loaded, cleaned and checked for quality problems, then shaped into report-ready tables. It runs on a synthetic dataset of about 8,600 members, 69,000 claims and 109,000 claim lines from a third-party administrator of self-funded health plans.

**Status:** in progress. Core pipeline complete; dbt models and tests are next.

## Architecture

```
CSV files ──► stage (@landing) ──► RAW ──► STAGING ──► MARTS
                                    │         │           │
                          exactly as received │   report-ready views
                                    cleaned, deduped, flagged
```

| Layer | What it holds | Rule |
|---|---|---|
| **RAW** | 14 tables loaded with `COPY INTO`, one per source file | Never edited. The record of what arrived. |
| **STAGING** | One view per raw table | Deduplicate, standardize codes, flag bad records. Flag, don't delete. |
| **MARTS** | Business-ready views and dimensions | All business rules built in, so reports can't get them wrong. |

## What's built

- **Repeatable load:** a Snowflake Scripting procedure, `load_raw(reload)`, loops over every raw table and runs `COPY INTO` from the stage. One call truncates and reloads all 14 tables.
- **Staging views:**
  - `QUALIFY ROW_NUMBER()` deduplication on claims and claim lines
  - Standardized gender codes and ZIP codes
  - Open-ended eligibility spans normalized to one convention
  - Boolean flags for paid claims, bad service dates and invalid spans
- **Paid claims mart:** joins claims to eligibility on the service date, keeps unmatched claims visible, and resolves overlapping eligibility spans with a documented "newest span wins" rule.
- **Incremental processing:** a stream on the claims table plus a scheduled task that processes only new rows and skips runs when nothing changed.
- **Change history:**
  - A `MERGE` that updates only rows that actually changed (null-safe comparison)
  - A Type 2 slowly changing member dimension using hash-based change detection and point-in-time joins
- **Recovery:** Time Travel and zero-copy cloning to restore a table from before a bad `UPDATE`, swapped back into place with `ALTER TABLE ... SWAP WITH`
- **Performance:** query profile analysis of partition pruning, cache behavior and warehouse sizing on a 69-million-row test table
- **Data quality checks:** `sql/10_data_quality_checks.sql` runs six checks after every load and lists the expected result for each.
- **Orchestration:** a three-step task graph (`sql/11_task_graph.sql`) runs the pipeline nightly:

  ```
  t_load_raw  ──►  t_dq_checks  ──►  t_publish_paid_claims
  ```

  The load reloads every RAW table. A stored procedure then runs the six data quality checks, logs each result to `ops.dq_results`, and raises an error if any is off. That error fails the run, so the published report table is only rebuilt from data that passed every check.

## Data quality issues caught

Every load is checked against expected row counts. The checks surfaced:

| Issue | Effect if missed |
|---|---|
| Claim rows extracted twice | Paid dollars overstated |
| Service dates keyed in the future | Bad trend lines |
| Gender recorded in mixed formats (M, Male, m, blank) | Wrong demographic splits |
| ZIP codes missing their leading zero | Failed geographic joins |
| Two conventions for "still covered" in eligibility | Claims silently dropped from joins |
| Overlapping eligibility spans for 25 members | Join fan-out that double-counted 30 claims |
| Paid claims with no eligibility on the service date | Money with no employer group |

## Repo layout

```
data/        14 source CSV files
generator/   Python script that rebuilds the synthetic data (fixed seed, same output every time)
docs/        data dictionary: every table and column, and how claims were priced and paid
sql/         Snowflake SQL, run in numbered order
```

## Rebuilding from scratch

1. Run `sql/00_setup.sql` (warehouse, database, schemas, file format, stage).
2. Run `sql/01_create_raw_tables.sql`.
3. Upload the files in `data/` to the `@landing` stage.
4. Run `sql/03_load_raw_proc.sql`, then `call claims_db.raw.load_raw(true);`
5. Run `sql/04_staging.sql`, then `sql/05_marts.sql`.
6. Run `sql/11_task_graph.sql` to build the scheduled pipeline and test it once.

## Tech

Snowflake (SQL, Snowflake Scripting, stored procedures, streams, tasks and task graphs, Time Travel, cloning), Python, Git

## About the data

All data is synthetic. No real people, providers or claims are included.
