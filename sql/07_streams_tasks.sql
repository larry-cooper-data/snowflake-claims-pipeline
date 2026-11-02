/*Snowflake	Oracle equivalent	What it does
Stream	Materialized view log / change capture	Tracks which rows were inserted, updated or deleted in a table since you last processed them
Task	DBMS_SCHEDULER job	Runs SQL or a procedure on a schedule, using a warehouse

VERY IMPORTANT A STREAM IS A LOG NOT LIKE A REAL MV, JUST A LOG OF THE CHANGES TO A TABLE SINCE LAST TIME*/



-- One time: SYSADMIN needs permission to run tasks
use role accountadmin;
grant execute task on account to role sysadmin;
use role sysadmin;
use database claims_db;

-- Start tracking changes on claims
create or replace stream claims_db.raw.claims_stream
  on table claims_db.raw.claims;

select count(*) from claims_db.raw.claims_stream;

insert into raw.claims
select * replace(
'NEW' || claim_id as claim_id
)
from raw.claims
limit 5;

select claim_id, claim_status, total_paid_amt, metadata$action, metadata$isupdate
from raw.claims_stream;


create table if not exists claims_db.raw.claims_arrival_log (
  claim_id       varchar,
  claim_status   varchar,
  total_paid_amt number(12,2),
  logged_at      timestamp_ltz default current_timestamp()
);

insert into claims_db.raw.claims_arrival_log (claim_id, claim_status, total_paid_amt)
select claim_id, claim_status, total_paid_amt
from raw.claims_stream
where metadata$action = 'INSERT';

select count(*) from claims_db.raw.claims_stream;
select * from claims_db.raw.claims_arrival_log;


--TASK
create or replace task claims_db.raw.log_new_claims
  warehouse = practice_wh
  schedule = '1 minute'
  when system$stream_has_data('claims_db.raw.claims_stream')
as
  insert into claims_db.raw.claims_arrival_log (claim_id, claim_status, total_paid_amt)
  select claim_id, claim_status, total_paid_amt
  from claims_db.raw.claims_stream
  where metadata$action = 'INSERT';


--altering tasks
alter task claims_db.raw.log_new_claims resume;
alter task claims_db.raw.log_new_claims suspend;


delete from claims_db.raw.claims where claim_id like 'NEW%';

select count(*) from claims_db.raw.claims;


show tasks in schema claims_db.raw;


insert into claims_db.raw.claims
select * replace ('NEW2' || claim_id as claim_id)
from claims_db.raw.claims
where claim_id not like 'NEW%'
limit 3;

select *
from claims_db.raw.claims_arrival_log
order by logged_at;


select *
from table(claims_db.information_schema.task_history(task_name => 'LOG_NEW_CLAIMS'))
order by scheduled_time desc
limit 5;

drop task claims_db.raw.log_new_claims;
drop stream claims_db.raw.claims_stream;
drop table claims_db.raw.claims_arrival_log;


delete from claims_db.raw.claims where claim_id like 'NEW%';

select count(*) from claims_db.raw.claims;
