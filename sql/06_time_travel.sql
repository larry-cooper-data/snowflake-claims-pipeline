
use role accountadmin;
grant ownership on table claims_db.raw.members_practice to role sysadmin copy current grants;
use role sysadmin;

create or replace table claims_db.raw.members_practice
  clone claims_db.raw.members;

select count(*) from claims_db.raw.members_practice;

update claims_db.raw.members_practice
set last_name = 'OOPS';

--01c7fe21-0209-4ce5-0012-54da0002d072

select * from claims_db.raw.members_practice;

select last_name, count(*)
from claims_db.raw.members_practice
  before(statement => '01c7fe21-0209-4ce5-0012-54da0002d072')
group by all
order by 2 desc
limit 10;


--clone table
create or replace table claims_db.raw.members_restored
clone claims_db.raw.members_practice
before(statement => '01c7fe21-0209-4ce5-0012-54da0002d072');


show tables in database claims_db;
drop table claims_db.raw.MEMBER_RESTORED;


select count(*)                    as members,
       count_if(last_name = 'OOPS') as oops_rows
from claims_db.raw.MEMBERS_PRACTICE;

--replace table with clone
alter table claims_db.raw.members_practice
swap with claims_db.raw.members_restored;


undrop table claims_db.raw.members_restored;

select count(*), count_if(last_name = 'OOPS')
from claims_db.raw.members_restored;


drop table claims_db.raw.members_restored;

undrop table claims_db.raw.members_restored;


--clone whole database
create database claims_dev clone claims_db;

show schemas in database claims_dev;

select count(*) from claims_dev.raw.claims;

truncate table claims_dev.raw.claims;

select count(*) from claims_dev.raw.claims;

select count(*) from claims_dev.staging.stg_claims;

select get_ddl('view', 'claims_dev.staging.stg_claims');

create or replace view claims_dev.staging.stg_claims as
select c.*,
       c.claim_status in ('P', 'A')          as is_paid_claim,
       c.service_from_date > c.received_date as is_bad_service_date
from raw.claims c
qualify row_number() over (partition by c.claim_id order by c.claim_id) = 1;

select count(*) from claims_dev.staging.stg_claims;

select count(*), sum(total_paid_amt)
from claims_db.marts.paid_claims;


drop database claims_dev;

drop table claims_db.raw.members_practice;