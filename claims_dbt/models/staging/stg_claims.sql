select c.*,
       c.claim_status in ('P', 'A')          as is_paid_claim,
       c.service_from_date > c.received_date as is_bad_service_date
from {{ source('raw', 'claims') }} c
qualify row_number() over (partition by c.claim_id order by c.claim_id) = 1