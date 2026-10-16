with src as (select * from {{ source('raw', 'completions') }})
select
    cast(completion_id as varchar)                  as completion_id,
    cast(application_id as varchar)                 as application_id,
    cast(funds_released_at as timestamp)            as funds_released_at,
    cast(loan_amount as decimal(14, 2))             as loan_amount,
    cast(product_id as varchar)                     as product_id,
    cast(rate_card_id as varchar)                   as rate_card_id,
    cast(initial_rate_pct as decimal(5, 2))         as initial_rate_pct,
    cast(fixed_years as integer)                    as fixed_years,
    cast(term_type as varchar)                      as term_type,
    cast(market_value as decimal(14, 2))            as market_value,
    cast(monthly_rent as decimal(10, 2))            as monthly_rent,
    cast(solicitor as varchar)                      as solicitor,
    cast(completion_fee_gbp as decimal(12, 2))      as completion_fee_gbp
from src
