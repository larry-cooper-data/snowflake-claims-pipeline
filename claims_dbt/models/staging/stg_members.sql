select * replace (
    trim(first_name) as first_name,
    trim(last_name)  as last_name,    
    decode(gender,'M','M','m','M','Male','M','F','F','f','F','Female','F','U') as gender,
    /*case
    when upper(gender) in ('M', 'MALE')   then 'M'
    when upper(gender) in ('F', 'FEMALE') then 'F'
    else 'U'
end as gender
case
    when upper(gender) in ('M', 'MALE')   then 'M'
    when upper(gender) in ('F', 'FEMALE') then 'F'
    else 'U'
end as gender
*/
CASE WHEN LENGTH(ADDRESS_ZIP) < 5 THEN
    LPAD(ADDRESS_ZIP,5,'0')
    ELSE
    ADDRESS_ZIP
END AS ADDRESS_ZIP
)
from {{source('raw', 'members')}}