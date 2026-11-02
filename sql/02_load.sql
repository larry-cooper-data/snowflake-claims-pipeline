
list @claims_db.raw.landing;



copy into claims_db.raw.plans
from @claims_db.raw.landing
files = ('plans.csv');


copy into claims_db.raw.claim_lines
from @claims_db.raw.landing
files = ('claim_lines.csv');

copy into claims_db.raw.claim_status_codes
from @claims_db.raw.landing
files = ('claim_status_codes.csv');

copy into claims_db.raw.claims
from @claims_db.raw.landing
files = ('claims.csv');




select * from claims_db.information_schema.tables
where table_schema = 'RAW';








select * from claims_db.raw.plans;

