use role sysadmin;

create or replace secure view claims_db.marts.paid_claims_secure as
select * from marts.paid_claims;

use role analyst;
use secondary roles none;

show views in schema claims_db.marts;


use role sysadmin;
use secondary roles all;


use role sysadmin;

create schema if not exists claims_db.sharing;

-- Who gets which group
create or replace table claims_db.sharing.group_access (
  group_id          varchar,
  consumer_account  varchar
);

insert into claims_db.sharing.group_access values
  ('G1001', 'BROKER_A'),
  ('G1002', 'BROKER_A'),
  ('G1003', 'STOPLOSS_B');

-- The view: you only get rows for groups mapped to YOUR account
create or replace secure view claims_db.sharing.group_paid_claims as
select p.*
from marts.paid_claims p,
     sharing.group_access a
where p.group_id = a.group_id
  and a.consumer_account = current_account();


select current_account();

select count(*) from claims_db.sharing.group_paid_claims;


alter session set simulated_data_sharing_consumer = 'BROKER_A';

select group_id, count(*)
from claims_db.sharing.group_paid_claims
group by group_id
order by group_id;

alter session set simulated_data_sharing_consumer = 'STOPLOSS_B';

select group_id, count(*)
from claims_db.sharing.group_paid_claims
group by group_id
order by group_id;

alter session unset simulated_data_sharing_consumer;

select group_id, count(*)
from claims_db.marts.paid_claims
where group_id in ('G1001', 'G1002', 'G1003')
group by group_id
order by group_id;


use role accountadmin;

create share claims_share;

grant usage  on database claims_db                         to share claims_share;
grant usage  on schema   claims_db.sharing                 to share claims_share;
grant select on view     claims_db.sharing.group_paid_claims to share claims_share;

show grants to share claims_share;


grant select on view claims_db.marts.paid_claims to share claims_share;

show shares;


select count(*) from snowflake_sample_data.tpch_sf1.orders;
delete from snowflake_sample_data.tpch_sf1.orders where 1 = 1;
