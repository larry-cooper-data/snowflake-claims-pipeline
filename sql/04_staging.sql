use role sysadmin;
use warehouse practice_wh;
use database claims_db;
create schema if not exists claims_db.staging;

show schemas in database claims_db;

create or replace view claims_db.staging.stg_claims as
select
    c.*,
    c.claim_status in ('P', 'A')           as is_paid_claim,
    c.service_from_date > c.received_date  as is_bad_service_date
from raw.claims c
qualify row_number() over (partition by c.claim_id order by c.claim_id) = 1;

select count(*)                                  as claims,
       sum(iff(is_paid_claim, total_paid_amt, 0)) as real_paid,
       count_if(is_bad_service_date)             as bad_dates
from claims_db.staging.stg_claims;

create or replace view claims_db.staging.stg_members as
select * replace (
    trim(first_name) as first_name,
    trim(last_name)  as last_name,    
    decode(gender,'M','M','m','M','Male','M','F','F','f','F','Female','F','U') as gender,
    /*case
    when upper(gender) in ('M', 'MALE')   then 'M'
    when upper(gender) in ('F', 'FEMALE') then 'F'
    else 'U'
end as gender
case
    when upper(gender) in ('M', 'MALE')   then 'M'
    when upper(gender) in ('F', 'FEMALE') then 'F'
    else 'U'
end as gender
*/
CASE WHEN LENGTH(ADDRESS_ZIP) < 5 THEN
    LPAD(ADDRESS_ZIP,5,'0')
    ELSE
    ADDRESS_ZIP
END AS ADDRESS_ZIP
)
from claims_db.raw.members;


select * from claims_db.raw.members;

select count(*) from claims_db.staging.stg_members;
select count(*) from claims_db.staging.stg_members where last_name <> trim(last_name);


select gender, count(*)
--from claims_db.raw.members
from claims_db.staging.stg_members
group by all
order by 2 desc;

select count(*)
from claims_db.staging.stg_members
where length(address_zip) < 5;

select member_id, address_state, address_zip
from claims_db.staging.stg_members
where address_state in ('MA', 'NJ', 'CT')
limit 10;


create or replace view claims_db.staging.stg_eligibility as
select * replace (
           coalesce(term_date, '9999-12-31') as term_date
       ),
       coalesce(term_date, '9999-12-31') >= effective_date as is_valid_span
from raw.eligibility;

select count(*)                           as spans,
       count_if(term_date is null)        as null_terms,
       count_if(not is_valid_span)        as bad_spans,
       count_if(is_valid_span is null)    as unknown
from claims_db.staging.stg_eligibility;


describe view claims_db.staging.stg_eligibility;

show tables in database claims_db;


select * from claims_db.raw.claim_lines;

create or replace view claims_db.staging.stg_claim_lines as
select * from claims_db.raw.claim_lines
qualify row_number() over (partition by claim_id, line_number order by claim_id, line_number) = 1;

select * from claims_db.staging.stg_claim_lines;

select count(*)                                       as line_rows,
       count(distinct claim_id || '-' || line_number) as unique_lines
from claims_db.staging.stg_claim_lines;


select count(*)                      as total_rows,
       count(distinct b.claim_id)    as distinct_claims,
       count_if(a.member_id is null) as no_match
from claims_db.staging.stg_claims b,
     claims_db.staging.stg_eligibility a
where b.member_id         = a.member_id(+)
  and b.service_from_date >= a.effective_date(+)
  and b.service_from_date <= a.term_date(+)
  and b.is_paid_claim;

  select b.claim_id, b.member_id, b.service_from_date,
       a.plan_code, a.effective_date, a.term_date
from claims_db.staging.stg_claims b,
     claims_db.staging.stg_eligibility a
where b.member_id         = a.member_id
  and b.service_from_date >= a.effective_date
  and b.service_from_date <= a.term_date
  and b.is_paid_claim
qualify count(*) over (partition by b.claim_id) > 1
order by b.claim_id;

select plan_code, term_date, count(*)
from claims_db.staging.stg_eligibility
where group_id = 'G1001'
group by all
order by 1, 2;