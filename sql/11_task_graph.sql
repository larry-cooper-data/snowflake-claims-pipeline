-- 11_task_graph.sql
-- Runs the whole pipeline as a Snowflake task graph (a DAG):
--
--   t_load_raw  ---->  t_dq_checks  ---->  t_publish_paid_claims
--   nightly reload     fails the run if    only runs when every
--   of all RAW tables  any check is off    check has passed
--
-- Oracle equivalent: a DBMS_SCHEDULER job chain. Each step starts only when
-- the step before it succeeds, so bad data never reaches the published table.
--
-- Pipeline bookkeeping lives in its own OPS schema. It can't go in RAW,
-- because load_raw() reloads every table in RAW.

use role sysadmin;
use warehouse practice_wh;

create schema if not exists claims_db.ops;


-- ============================================================
-- 1. Table that keeps every data quality result
-- ============================================================
create table if not exists claims_db.ops.dq_results (
  run_at      timestamp_ltz,
  check_name  varchar,
  expected    number(18,2),
  actual      number(18,2),
  passed      boolean
);


-- ============================================================
-- 2. Data quality procedure
--    The six checks from 10_data_quality_checks.sql, logged to
--    ops.dq_results. If any result is off it raises an error,
--    which fails the task and stops the graph.
--    Expected values are the issues planted in the dataset.
-- ============================================================
create or replace procedure claims_db.ops.run_dq_checks()
  returns varchar
  language sql
  execute as owner
as
$$
declare
  dq_failed exception (-20001, 'Data quality checks failed. See claims_db.ops.dq_results.');
  run_ts    timestamp_ltz default current_timestamp();
  fails     integer default 0;
begin
  insert into claims_db.ops.dq_results (run_at, check_name, expected, actual, passed)
  select :run_ts, check_name, expected, actual, equal_null(actual, expected)
  from (
    select 'Empty raw tables' as check_name,
           0 as expected,
           (select count(*)
              from claims_db.information_schema.tables
             where table_schema = 'RAW'
               and table_type   = 'BASE TABLE'
               and row_count    = 0) as actual
    union all
    select 'Duplicate claim IDs in RAW', 12,
           (select count(*)
              from (select claim_id
                      from claims_db.raw.claims
                     group by claim_id
                    having count(*) > 1))
    union all
    select 'Service date after received date', 3,
           (select count_if(is_bad_service_date)
              from claims_db.staging.stg_claims)
    union all
    select 'Overlapping eligibility spans', 25,
           (select count(*)
              from claims_db.staging.stg_eligibility a,
                   claims_db.staging.stg_eligibility b
             where a.member_id       = b.member_id
               and a.eligibility_id  < b.eligibility_id
               and a.effective_date <= b.term_date
               and b.effective_date <= a.term_date
               and a.is_valid_span
               and b.is_valid_span)
    union all
    select 'Paid claims with no eligibility', 45,
           (select count_if(is_no_eligibility)
              from claims_db.marts.paid_claims)
    union all
    select 'Mart paid minus staging paid', 0,
           (select sum(total_paid_amt) from claims_db.marts.paid_claims)
         - (select sum(total_paid_amt) from claims_db.staging.stg_claims where is_paid_claim)
  );

  select count_if(not passed) into :fails
    from claims_db.ops.dq_results
   where run_at = :run_ts;

  if (fails > 0) then
    raise dq_failed;
  end if;

  return 'All 6 data quality checks passed';
end;
$$;

-- Test it by itself before building the tasks. Expected: 'All 6 data quality checks passed'
call claims_db.ops.run_dq_checks();

select * from claims_db.ops.dq_results order by run_at desc, check_name;


-- ============================================================
-- 3. The task graph
--    Tasks are created suspended, so nothing runs yet.
--    All tasks in a graph must live in the same schema (OPS).
--    To rerun this section later, suspend the root task first.
-- ============================================================

-- One time (already done in 07): SYSADMIN needs permission to run tasks
-- use role accountadmin;
-- grant execute task on account to role sysadmin;
-- use role sysadmin;

-- Root: nightly full reload of the 14 RAW tables
create or replace task claims_db.ops.t_load_raw
  warehouse = practice_wh
  schedule = 'using cron 0 11 * * * UTC'
  suspend_task_after_num_failures = 3
  comment = 'Root: truncate and reload all RAW tables from @landing'
as
  call claims_db.raw.load_raw(true);

-- Step 2: data quality gate
create or replace task claims_db.ops.t_dq_checks
  warehouse = practice_wh
  comment = 'Runs the six data quality checks; fails the graph if any is off'
  after claims_db.ops.t_load_raw
as
  call claims_db.ops.run_dq_checks();

-- Step 3: publish the report table, only after the checks pass
create or replace task claims_db.ops.t_publish_paid_claims
  warehouse = practice_wh
  comment = 'Materializes marts.paid_claims into a table for reporting'
  after claims_db.ops.t_dq_checks
as
  create or replace table claims_db.marts.paid_claims_published as
  select * from claims_db.marts.paid_claims;

-- Shows the three tasks and how they link
select name, predecessors, schedule, state
from table(claims_db.information_schema.task_dependents(
       task_name => 'claims_db.ops.t_load_raw', recursive => true));


-- ============================================================
-- 4. Test run, by hand
--    Resume the two child tasks but leave the root suspended, so the
--    nightly schedule doesn't burn trial credits. EXECUTE TASK runs
--    a suspended root once; suspended child tasks would be skipped.
-- ============================================================
alter task claims_db.ops.t_publish_paid_claims resume;
alter task claims_db.ops.t_dq_checks resume;

execute task claims_db.ops.t_load_raw;

-- Watch it run (a minute or two). Each step shows SCHEDULED, EXECUTING,
-- SUCCEEDED, FAILED or SKIPPED. Rerun this query until all three say SUCCEEDED.
-- In Snowsight, open T_LOAD_RAW: the Graph tab draws the DAG and the
-- Run History tab shows each run.
select name, state, scheduled_time, completed_time, return_value, error_message
from table(claims_db.information_schema.task_history(
       scheduled_time_range_start => dateadd(hour, -1, current_timestamp())))
where schema_name = 'OPS'
order by scheduled_time desc;

select * from claims_db.ops.dq_results order by run_at desc, check_name;

select count(*) from claims_db.marts.paid_claims_published;


-- ============================================================
-- 5. Prove the gate works: plant one more duplicate claim
-- ============================================================
insert into claims_db.raw.claims
select *
from claims_db.raw.claims
where claim_id not in (select claim_id
                         from claims_db.raw.claims
                        group by claim_id
                       having count(*) > 1)
limit 1;

-- Errors on purpose: Data quality checks failed
call claims_db.ops.run_dq_checks();

-- Expected: Duplicate claim IDs in RAW, expected 12, actual 13
select * from claims_db.ops.dq_results
where not passed
order by run_at desc;

-- When a check fails during a graph run, t_publish_paid_claims never runs,
-- so the published table keeps the last good data. Reload to clean up:
call claims_db.raw.load_raw(true);


-- ============================================================
-- 6. Turn the schedule on, or shut everything off
-- ============================================================
-- Nightly schedule on (uses credits every night):
-- alter task claims_db.ops.t_load_raw resume;

-- After a failed scheduled run, retry from the step that failed:
-- execute task claims_db.ops.t_load_raw retry last;

-- Everything off (root first):
alter task claims_db.ops.t_load_raw suspend;
alter task claims_db.ops.t_dq_checks suspend;
alter task claims_db.ops.t_publish_paid_claims suspend;
