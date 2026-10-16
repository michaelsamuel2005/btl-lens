with src as (select * from {{ source('raw', 'offers') }})
select
    cast(offer_id as varchar)                       as offer_id,
    cast(application_id as varchar)                 as application_id,
    cast(offered_at as timestamp)                   as offered_at,
    cast(offer_expiry as timestamp)                 as offer_expiry,
    cast(loan_amount as decimal(14, 2))             as loan_amount,
    cast(product_id as varchar)                     as product_id,
    cast(rate_card_id as varchar)                   as rate_card_id,
    cast(initial_rate_pct as decimal(5, 2))         as initial_rate_pct,
    cast(stress_rate_pct as decimal(5, 2))          as stress_rate_pct,
    cast(ltv_pct as decimal(5, 1))                  as ltv_pct,
    cast(rental_cover_pct as decimal(6, 1))         as rental_cover_pct_as_offered,
    cast(offer_accepted_at as timestamp)            as offer_accepted_at
from src
