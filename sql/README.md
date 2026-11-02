# SQL files

Copy your files from the Snowflake workspace into this folder, keeping these names. Run them in numbered order.

| File | What it does |
|---|---|
| 00_setup.sql | Warehouse, database, schemas, file format, stage |
| 01_create_raw_tables.sql | The 14 RAW tables |
| 02_load.sql | One COPY INTO per table (the manual version) |
| 03_load_raw_proc.sql | The `load_raw` procedure that loads every table in a loop |
| 04_staging.sql | Staging views: dedupe, standardize, flag |
| 05_marts.sql | The paid claims mart |
| 06_time_travel.sql | Time Travel, clone, SWAP and UNDROP practice |
| 07_streams_tasks.sql | Stream and scheduled task practice |
| 08_merge.sql | MERGE and the Type 2 member dimension |
| 09_performance.sql | Cache, pruning and warehouse sizing tests |

Delete this README once your files are in, or leave it as the index.
