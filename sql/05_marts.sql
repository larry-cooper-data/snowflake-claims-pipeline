use role sysadmin;
use warehouse practice_wh;
use schema claims_db.raw;

create schema if not exists claims_db.marts;

create or replace view claims_db.marts.paid_claims as
select b.claim_id,
       b.member_id,
       a.group_id,
       a.plan_code,
       b.claim_type,
       b.service_from_date,
       b.paid_date,
       b.total_allowed_amt,
       b.total_paid_amt,
       a.member_id is null as is_no_eligibility
from claims_db.staging.stg_claims b,
     claims_db.staging.stg_eligibility a
where b.member_id         = a.member_id(+)
  and b.service_from_date >= a.effective_date(+)
  and b.service_from_date <= a.term_date(+)
  and b.is_paid_claim
qualify row_number() over (partition by b.claim_id order by a.effective_date desc) = 1;

select count(*)                    as claims,
       count(distinct claim_id)    as distinct_claims,
       count_if(is_no_eligibility) as no_elig,
       sum(total_paid_amt)         as paid
from claims_db.marts.paid_claims;


select coalesce(group_id, 'NO ELIGIBILITY') as group_id,
       count(*)                             as claims,
       sum(total_paid_amt)                  as paid
from claims_db.marts.paid_claims
group by all
order by paid desc;