with src as (select * from {{ source('raw', 'funding_partners') }})
select
    cast(partner_id as varchar)                     as partner_id,
    cast(partner_name as varchar)                   as partner_name,
    cast(line_start as date)                        as line_start,
    cast(line_end as date)                          as line_end,
    cast(monthly_capacity_gbp as decimal(14, 2))    as monthly_capacity_gbp,
    cast(scope as varchar)                          as scope
from src
