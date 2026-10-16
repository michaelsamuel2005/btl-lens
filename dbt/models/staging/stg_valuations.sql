with src as (select * from {{ source('raw', 'valuations') }})
select
    cast(valuation_id as varchar)                   as valuation_id,
    cast(application_id as varchar)                 as application_id,
    cast(valuation_type as varchar)                 as valuation_type,
    cast(instructed_at as timestamp)                as instructed_at,
    cast(received_at as timestamp)                  as received_at,
    cast(market_value as decimal(14, 2))            as market_value,
    cast(monthly_rent_assessed as decimal(10, 2))   as monthly_rent_assessed,
    cast(property_type_assessed as varchar)         as property_type_assessed,
    cast(provider as varchar)                       as provider,
    cast(fee_gbp as decimal(10, 2))                 as fee_gbp
from src
