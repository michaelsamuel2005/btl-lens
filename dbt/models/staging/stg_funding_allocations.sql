with src as (select * from {{ source('raw', 'funding_allocations') }})
select
    cast(allocation_id as varchar)                  as allocation_id,
    cast(completion_id as varchar)                  as completion_id,
    cast(partner_id as varchar)                     as partner_id,
    cast(allocated_amount as decimal(14, 2))        as allocated_amount,
    cast(allocation_month as date)                  as allocation_month
from src
