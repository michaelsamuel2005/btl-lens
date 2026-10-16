select
    rc.rate_card_id,
    rc.product_id,
    p.product_range,
    p.term_label,
    rc.version,
    rc.valid_from,
    rc.valid_to,
    rc.valid_to is null                                  as is_current,
    rc.initial_rate_pct,
    rc.tracker_margin_pct,
    rc.reversion_margin_pct,
    rc.initial_rate_pct - lag(rc.initial_rate_pct) over (partition by rc.product_id order by rc.version) as rate_change_pct_points
from {{ ref('stg_rate_cards') }} rc
join {{ ref('stg_products') }} p on p.product_id = rc.product_id
