select * 
from {{source('raw','claim_lines')}}
qualify row_number() over (partition by claim_id, line_number order by claim_id, line_number) = 1