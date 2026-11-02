use role sysadmin;


create warehouse practice_wh
warehouse_size = 'xsmall'
auto_suspend = 60
auto_resume = true
initially_suspended = true;

create database if not exists claims_db;
create schema if not exists claims_db.raw;


use schema claims_db.raw;


create file format if not exists claims_db.raw.csv_fmt
  type = csv
  skip_header = 1
  field_optionally_enclosed_by = '"'
  empty_field_as_null = true
  null_if = ('');

create stage if not exists claims_db.raw.landing
  file_format = claims_db.raw.csv_fmt;
