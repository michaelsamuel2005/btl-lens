with src as (select * from {{ source('raw', 'rate_cards') }})
select
    cast(rate_card_id as varchar)                   as rate_card_id,
    cast(product_id as varchar)                     as product_id,
    cast(version as integer)                        as version,
    cast(valid_from as date)                        as valid_from,
    cast(valid_to as date)                          as valid_to,
    cast(initial_rate_pct as decimal(5, 2))         as initial_rate_pct,
    cast(tracker_margin_pct as decimal(5, 2))       as tracker_margin_pct,
    cast(reversion_margin_pct as decimal(5, 2))     as reversion_margin_pct
from src
