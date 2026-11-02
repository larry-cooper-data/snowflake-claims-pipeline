use role sysadmin;
use database claims_db;
use schema marts;


create or replace table claims_db.marts.dim_member (
  member_id      varchar,
  subscriber_id  varchar,
  first_name     varchar,
  last_name      varchar,
  birth_date     date,
  gender         varchar,
  address_state  varchar,
  address_zip    varchar,
  updated_at     timestamp_ltz
);

merge into claims_db.marts.dim_member t
using claims_db.staging.members_extract s
  on t.member_id = s.member_id
when matched and (
t.first_name    is distinct from s.first_name or
  t.last_name     is distinct from s.last_name or
  t.birth_date    is distinct from s.birth_date or
  t.gender        is distinct from s.gender or
  t.address_state is distinct from s.address_state or
  t.address_zip   is distinct from s.address_zip
) then update set
  t.first_name    = s.first_name,
  t.last_name     = s.last_name,
  t.birth_date    = s.birth_date,
  t.gender        = s.gender,
  t.address_state = s.address_state,
  t.address_zip   = s.address_zip,
  t.updated_at    = current_timestamp()
when not matched then insert
  (member_id, subscriber_id, first_name, last_name, birth_date,
   gender, address_state, address_zip, updated_at)
values
  (s.member_id, s.subscriber_id, s.first_name, s.last_name, s.birth_date,
   s.gender, s.address_state, s.address_zip, current_timestamp());


create or replace table claims_db.staging.members_extract as
select * from claims_db.staging.stg_members;

-- The Hoffmann family (3 members) moved to Arizona
update claims_db.staging.members_extract
set address_state = 'AZ',
    address_zip   = '85296'
where subscriber_id = 'M0000001';

-- A new hire and spouse enrolled
insert into claims_db.staging.members_extract
  (member_id, subscriber_id, relationship_code, first_name, last_name,
   birth_date, gender, address_state, address_zip)
values
  ('M0009001', 'M0009001', 'SUB', 'Dale',  'Brenner', '1984-03-12', 'M', 'WI', '54481'),
  ('M0009002', 'M0009001', 'SPS', 'Paula', 'Brenner', '1986-07-02', 'F', 'WI', '54481');

select count(*) from claims_db.staging.members_extract;

select * from claims_db.staging.stg_members
where subscriber_id = 'M0000001';


create or replace table claims_db.marts.dim_member_hist (
  member_id      varchar,
  subscriber_id  varchar,
  first_name     varchar,
  last_name      varchar,
  birth_date     date,
  gender         varchar,
  address_state  varchar,
  address_zip    varchar,
  row_hash       number,
  valid_from     date,
  valid_to       date,
  is_current     boolean
);

insert into claims_db.marts.dim_member_hist
select member_id, subscriber_id, first_name, last_name, birth_date,
       gender, address_state, address_zip,
       hash(first_name, last_name, birth_date, gender, address_state, address_zip),
       '1900-01-01', '9999-12-31', true
from claims_db.staging.stg_members;

select * from dim_member_hist where member_id = 'M0000002';

select count(*), count_if(is_current) from dim_member_hist;


update claims_db.marts.dim_member_hist t
set valid_to   = dateadd(day, -1, current_date),
    is_current = false
from claims_db.staging.members_extract s
where t.member_id = s.member_id
  and t.is_current
  and t.row_hash <> hash(s.first_name, s.last_name, s.birth_date,
                         s.gender, s.address_state, s.address_zip);


insert into claims_db.marts.dim_member_hist
select s.member_id, s.subscriber_id, s.first_name, s.last_name, s.birth_date,
       s.gender, s.address_state, s.address_zip,
       hash(s.first_name, s.last_name, s.birth_date,
            s.gender, s.address_state, s.address_zip),
       current_date, '9999-12-31', true
from claims_db.staging.members_extract s
where not exists (select 1
                  from claims_db.marts.dim_member_hist t
                  where t.member_id = s.member_id
                    and t.is_current);

select member_id, first_name, address_state, valid_from, valid_to, is_current
from claims_db.marts.dim_member_hist
where subscriber_id = 'M0000001'
order by member_id, valid_from;                    


select c.claim_id, c.member_id, c.service_from_date, h.address_state
from claims_db.marts.paid_claims c,
     claims_db.marts.dim_member_hist h
where c.member_id = h.member_id
  and c.service_from_date between h.valid_from and h.valid_to
  and h.subscriber_id = 'M0000001'
order by c.service_from_date desc
limit 10;

select c.claim_id, c.member_id, c.service_from_date, d.address_state
from claims_db.marts.paid_claims c,
     claims_db.marts.dim_member d
where c.member_id = d.member_id
  and d.subscriber_id = 'M0000001'
order by c.service_from_date desc
limit 10;

drop table claims_db.staging.members_extract;
drop table claims_db.marts.dim_member;
drop table claims_db.marts.dim_member_hist;

