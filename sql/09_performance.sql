/*Cache            Where it lives	              How long	                                           Cost
Result cache	   Snowflake’s services layer	  24 hours, if the query text and data are unchanged   Free
Warehouse cache	   The warehouse’s local disk	  Until the warehouse suspends	                       Speeds up queries that run anyway
Metadata	       Snowflake’s services layer	  Always	                                           Free (COUNT/MIN/MAX on a table)*/

--Step 1 the result cache
--first run 3.9s, second run 386ms
select group_id, count(*) as claims, sum(total_paid_amt) as paid
from claims_db.marts.paid_claims
group by all
order by paid desc;

--Step 2 turing off results cache rerun 762ms
alter session set use_cached_result = false;

alter warehouse practice_wh suspend;

select count(*), min(service_from_date), max(service_from_date)
from claims_db.raw.claims;

show warehouses like 'PRACTICE_WH';

--third cache metadata


create or replace table claims_db.raw.claims_big as
select c.* replace (
         c.claim_id || '-' || g.n                 as claim_id,
         dateadd(day, -g.n, c.service_from_date)  as service_from_date
       )
from claims_db.raw.claims c,
     (select seq4() as n from table(generator(rowcount => 1000))) g
order by service_from_date;


select count(*) from claims_db.raw.claims_big;


select count(*), sum(total_paid_amt)
from claims_db.raw.claims_big
where service_from_date between '2026-09-01' and '2026-09-30';

select count(*), sum(total_paid_amt)
from claims_db.raw.claims_big
where member_id = 'M0000001';


create or replace table claims_db.raw.claims_big_by_member as
select * from claims_db.raw.claims_big
order by member_id;


select count(*), sum(total_paid_amt)
from claims_db.raw.claims_big_by_member
where member_id = 'M0000001';

select count(*), sum(total_paid_amt)
from claims_db.raw.claims_big_by_member
where service_from_date between '2026-09-01' and '2026-09-30';

select system$clustering_information('claims_db.raw.claims_big', '(service_from_date)');

alter session set use_cached_result = false;

--4.0s --2.3s --3.1s
select member_id,
       count(distinct claim_id)   as claims,
       sum(total_paid_amt)        as paid
from claims_db.raw.claims_big
group by member_id
order by paid desc
limit 20;

alter warehouse practice_wh set warehouse_size = 'medium';
alter warehouse practice_wh set warehouse_size = 'xsmall';


drop table claims_db.raw.claims_big;
drop table claims_db.raw.claims_big_by_member;
alter session set use_cached_result = true;
show warehouses like 'PRACTICE_WH';