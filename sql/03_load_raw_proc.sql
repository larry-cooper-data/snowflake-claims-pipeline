use role sysadmin;
use warehouse practice_wh;
use schema claims_db.raw;

create or replace procedure claims_db.raw.load_raw(reload boolean)
  returns varchar
  language sql
  execute as owner
as
$$
declare
  c1 cursor for
    select table_name
    from claims_db.information_schema.tables
    where table_schema = 'RAW'
      and table_type = 'BASE TABLE'
    order by table_name;
  sql_text varchar;
  done varchar default '';
begin
  for rec in c1 do
    if (reload) then
      sql_text := 'truncate table claims_db.raw.' || rec.table_name;
      execute immediate :sql_text;
    end if;

    sql_text := 'copy into claims_db.raw.' || rec.table_name ||
                ' from @claims_db.raw.landing files = (''' ||
                lower(rec.table_name) || '.csv'')';
    if (reload) then
      sql_text := sql_text || ' force = true';
    end if;
    execute immediate :sql_text;

    done := done || rec.table_name || ' ';
  end for;
  return 'Loaded: ' || done;
end;
$$;

call claims_db.raw.load_raw(true);

select * from claims_db.information_schema.tables
where table_schema = 'RAW';

--1
select claim_status, sum(total_paid_amt) from claims_db.raw.claims
group by claim_status;

--2
select * from claims_db.raw.claims
qualify count(*) over (partition by claim_id order by claim_id) > 1
order by claim_id;

select * from claims_db.raw.claim_status_codes;


/*Paid by month. Total paid by service month, using DATE_TRUNC, counting only the statuses that are real money. Look at the last few months. What do you notice, and why?*/

select date_trunc('month', service_from_date) service_date, sum(total_paid_amt) from claims_db.raw.claims
where claim_status in ('A','P')
group by all;