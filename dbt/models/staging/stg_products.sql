with src as (select * from {{ source('raw', 'products') }})
select
    cast(product_id as varchar)                     as product_id,
    cast(product_range as varchar)                  as product_range,
    cast(property_scope as varchar)                 as property_scope,
    cast(borrower_scope as varchar)                 as borrower_scope,
    cast(term_type as varchar)                      as term_type,
    cast(fixed_years as integer)                    as fixed_years,
    cast(max_ltv_pct as decimal(5, 1))              as max_ltv_pct,
    cast(fee_pct as decimal(4, 2))                  as fee_pct,
    cast(purposes as varchar)                       as purposes,
    cast(erc_applies as boolean)                    as erc_applies,
    case when term_type = 'fixed' then cast(fixed_years as varchar) || '-year fixed'
         else cast(fixed_years as varchar) || '-year tracker' end as term_label
from src
