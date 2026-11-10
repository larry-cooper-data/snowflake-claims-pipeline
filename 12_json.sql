use role sysadmin;

create or replace table claims_db.raw.claims_json as
select object_construct(
         'claim_id',     c.claim_id,
         'member_id',    c.member_id,
         'status',       c.claim_status,
         'service_date', c.service_from_date,
         'total_paid',   c.total_paid_amt,
         'lines', array_agg(object_construct(
                    'line',      l.line_number,
                    'procedure', l.procedure_code,
                    'revenue',   l.revenue_code,
                    'paid',      l.paid_amt)) within group (order by l.line_number)
       ) as v
from claims_db.staging.stg_claims c,
     claims_db.staging.stg_claim_lines l
where c.claim_id = l.claim_id
  and c.claim_id in (select claim_id from claims_db.staging.stg_claims
                     where is_paid_claim limit 100)
group by c.claim_id, c.member_id, c.claim_status, c.service_from_date, c.total_paid_amt;

select * from claims_db.raw.claims_json limit 3;


select v:claim_id::varchar        as claim_id,
       v:member_id::varchar       as member_id,
       v:status::varchar          as status,
       v:service_date::date       as service_date,
       v:total_paid::number(12,2) as total_paid
from claims_db.raw.claims_json
limit 5;

select j.v:claim_id::varchar         as claim_id,
       f.value:line::number          as line_number,
       f.value:procedure::varchar    as procedure_code,
       f.value:revenue::varchar      as revenue_code,
       f.value:paid::number(12,2)    as paid_amt
from claims_db.raw.claims_json j,
     lateral flatten(input => j.v:lines) f
order by claim_id, line_number;


-- lines that came out of the JSON
select count(*)
from claims_db.raw.claims_json j,
     lateral flatten(input => j.v:lines) f;

-- the same claims' lines in the original table
select count(*)
from claims_db.staging.stg_claim_lines
where claim_id in (select v:claim_id::varchar from claims_db.raw.claims_json);


use role sysadmin;

copy into @claims_db.raw.landing/json/export
from claims_db.raw.claims_json
file_format = (type = json)
overwrite = true;

list @claims_db.raw.landing/json/;

copy into @claims_db.raw.landing/json/export
from claims_db.raw.claims_json
file_format = (type = json)
overwrite = true;


-------------------------
-- 1. A file format that tells Snowflake "these files are JSON"
create or replace file format claims_db.raw.json_fmt
  type = json
  strip_outer_array = true;

-- 2. A landing table: just one VARIANT column, no column design needed
create or replace table claims_db.raw.claims_json_loaded (v variant);

-- 3. Load it
copy into claims_db.raw.claims_json_loaded
from @claims_db.raw.landing/json/
file_format = (format_name = 'claims_db.raw.json_fmt');

select count(*) from claims_db.raw.claims_json_loaded;

------------------------------------
create or replace view claims_db.staging.stg_claim_lines_json as
select j.v:claim_id::varchar        as claim_id,
       j.v:member_id::varchar       as member_id,
       j.v:status::varchar          as claim_status,
       j.v:service_date::date       as service_from_date,
       f.value:line::number         as line_number,
       f.value:procedure::varchar   as procedure_code,
       f.value:revenue::varchar     as revenue_code,
       f.value:paid::number(12,2)   as paid_amt
from raw.claims_json_loaded j,
     lateral flatten(input => j.v:lines) f;

     select count(*), sum(paid_amt)
from claims_db.staging.stg_claim_lines_json;

select count(*), sum(paid_amt)
from claims_db.staging.stg_claim_lines
where claim_id in (select v:claim_id::varchar from claims_db.raw.claims_json_loaded);
