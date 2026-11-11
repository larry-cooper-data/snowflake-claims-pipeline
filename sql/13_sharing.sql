-- 13_sharing.sql
-- Secure views and Secure Data Sharing: share live claims with outside partners,
-- each one seeing only its own employer groups. No files, no copies.

use role sysadmin;

-- 1. A secure view hides its SQL from everyone but the owner
create or replace secure view claims_db.marts.paid_claims_secure as
select * from marts.paid_claims;

-- 2. Access table: which partner account gets which employer group
create schema if not exists claims_db.sharing;

create or replace table claims_db.sharing.group_access (
  group_id          varchar,
  consumer_account  varchar
);

insert into claims_db.sharing.group_access values
  ('G1001', 'BROKER_A'),
  ('G1002', 'BROKER_A'),
  ('G1003', 'STOPLOSS_B');

-- 3. One view for every partner; current_account() decides which rows they get
create or replace secure view claims_db.sharing.group_paid_claims as
select p.*
from marts.paid_claims p,
     sharing.group_access a
where p.group_id = a.group_id
  and a.consumer_account = current_account();

-- 4. Test as each partner before sharing
alter session set simulated_data_sharing_consumer = 'BROKER_A';
select group_id, count(*) from claims_db.sharing.group_paid_claims
group by group_id order by group_id;   -- G1001 and G1002 only

alter session set simulated_data_sharing_consumer = 'STOPLOSS_B';
select group_id, count(*) from claims_db.sharing.group_paid_claims
group by group_id order by group_id;   -- G1003 only

alter session unset simulated_data_sharing_consumer;

-- 5. Create the share: only the secure view goes in
use role accountadmin;

create share if not exists claims_share;
grant usage  on database claims_db                           to share claims_share;
grant usage  on schema   claims_db.sharing                   to share claims_share;
grant select on view     claims_db.sharing.group_paid_claims to share claims_share;

show grants to share claims_share;

-- Regular views are refused while secure_objects_only = true (the default):
-- grant select on view claims_db.marts.paid_claims to share claims_share;

-- 6. With a real partner (needs a second account):
-- alter share claims_share add accounts = partnerorg.partneraccount;
-- Partner side, one line:
-- create database claims_from_tpa from share providerorg.provideraccount.claims_share;