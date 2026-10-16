{#- The rate card that was live for each application's product on the day it was submitted. Offers are expected to
    be priced on this card (the rate is locked at submission). -#}
with a as (
    select application_id, product_id, submitted_at from {{ ref('stg_applications') }}
),
rc as (
    select * from {{ ref('stg_rate_cards') }}
)
select
    a.application_id,
    rc.rate_card_id      as rate_card_id_expected,
    rc.initial_rate_pct  as initial_rate_pct_expected,
    rc.tracker_margin_pct as tracker_margin_pct_expected
from a
join rc
  on rc.product_id = a.product_id
 and cast(a.submitted_at as date) >= rc.valid_from
 and cast(a.submitted_at as date) <= coalesce(rc.valid_to, cast('9999-12-31' as date))
