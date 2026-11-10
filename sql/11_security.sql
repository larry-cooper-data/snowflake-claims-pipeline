/*Concept	One line
Privileges go to roles	Never directly to users. Users are given roles.
Role tree	Grant custom roles to SYSADMIN
Reading one view needs 4 grants	Warehouse usage, database usage, schema usage, select
Future grants	on future views in schema ... covers objects created later
Secondary roles	All your roles are active at once, so test with them off or with a separate test user
Views run as their owner	Readers don’t need access to the tables underneath, so you can expose curated data and keep RAW locked
Masking policy	Column-level, applied at query time by role. The data isn’t changed. Enterprise edition and up.
Row access policy	The same idea for rows, like an analyst who only sees one employer group’s claims. You’ll see it on the exam.
Secure view	Hides the view’s SQL from people who don’t own it. Required for data sharing.*/


use role useradmin;

create role if not exists analyst;

grant role analyst to role sysadmin;

set me = current_user();
grant role analyst to user identifier($me);

show grants of role analyst;

-----------------------------
use role sysadmin;

grant usage on warehouse practice_wh to role analyst;
grant usage on database claims_db to role analyst;
grant usage on schema claims_db.marts to role analyst;
grant select on all views in schema claims_db.marts to role analyst;
grant select on future views in schema claims_db.marts to role analyst;

show grants of role analyst;

use role analyst;

select count(*), sum(total_paid_amt)
from claims_db.marts.paid_claims;

select count(*) from claims_db.raw.claims;


use role analyst;
use secondary roles none;

use secondary roles all;
use role sysadmin;

-----------------------------
use role sysadmin;

create or replace masking policy claims_db.raw.mask_name as (val varchar)
  returns varchar ->
  case when current_role() in ('SYSADMIN', 'ACCOUNTADMIN') then val
       else '*** MASKED ***'
  end;

create or replace masking policy claims_db.raw.mask_birth_date as (val date)
  returns date ->
  case when current_role() in ('SYSADMIN', 'ACCOUNTADMIN') then val
       else date_trunc('year', val)
  end;

alter table claims_db.raw.members modify column last_name
  set masking policy claims_db.raw.mask_name;

alter table claims_db.raw.members modify column birth_date
  set masking policy claims_db.raw.mask_birth_date;


select member_id, last_name, birth_date from claims_db.raw.members limit 3;


use role sysadmin;
grant usage on schema claims_db.staging to role analyst;
grant select on view claims_db.staging.stg_members to role analyst;


use role analyst;
select member_id, first_name, last_name, birth_date
from claims_db.staging.stg_members
limit 5;

use role sysadmin;
