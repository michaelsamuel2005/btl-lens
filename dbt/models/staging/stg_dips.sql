with src as (select * from {{ source('raw', 'dips') }})
select
    cast(dip_id as varchar)                         as dip_id,
    cast(broker_id as varchar)                      as broker_id,
    cast(created_at as timestamp)                   as created_at,
    cast(borrower_type as varchar)                  as borrower_type,
    cast(tax_band as varchar)                       as tax_band,
    cast(property_type as varchar)                  as property_type,
    cast(purpose as varchar)                        as purpose,
    cast(region as varchar)                         as region,
    cast(postcode_area as varchar)                  as postcode_area,
    cast(portfolio_size as integer)                 as portfolio_size,
    cast(property_value_est as decimal(14, 2))      as property_value_est,
    cast(loan_requested as decimal(14, 2))          as loan_requested,
    cast(monthly_rent_est as decimal(10, 2))        as monthly_rent_est,
    cast(ltv_requested_pct as decimal(5, 1))        as ltv_requested_pct,
    cast(product_id as varchar)                     as product_id,
    cast(dip_result as varchar)                     as dip_result
from src
