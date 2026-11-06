select * replace (
           coalesce(term_date, '9999-12-31') as term_date
       ),
       coalesce(term_date, '9999-12-31') >= effective_date as is_valid_span
from {{source('raw','eligibility')}}