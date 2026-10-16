{#- One row per offer, with the pricing that should have applied and the policy rental cover. -#}
with o as (
    select * from {{ ref('stg_offers') }}
),
x as (
    select * from {{ ref('int_rate_card_at_submission') }}
),
rc as (
    select * from {{ ref('int_rental_cover') }}
),
a as (
    select application_id, broker_id, submitted_at, purpose, property_type, is_resubmission from {{ ref('stg_applications') }}
)
select
    o.offer_id,
    o.application_id,
    a.broker_id,
    o.product_id,
    o.offered_at,
    {{ month_start('o.offered_at') }}                as offered_month,
    o.offer_expiry,
    o.loan_amount,
    o.ltv_pct,
    o.initial_rate_pct,
    o.stress_rate_pct                                as stress_rate_as_offered_pct,
    o.rental_cover_pct_as_offered,
    o.rate_card_id,
    x.rate_card_id_expected,
    o.rate_card_id = x.rate_card_id_expected         as priced_on_expected_card,
    x.initial_rate_pct_expected,
    o.initial_rate_pct - x.initial_rate_pct_expected as rate_difference_pct_points,
    rc.stress_rate_policy_pct,
    rc.rental_cover_policy_pct,
    rc.min_rental_cover_pct,
    rc.rental_cover_passes,
    o.offer_accepted_at,
    o.offer_accepted_at is not null                  as is_accepted,
    {{ days_between('o.offered_at', 'o.offer_accepted_at') }} as days_to_acceptance
from o
join a   on a.application_id = o.application_id and not a.is_resubmission
left join x  on x.application_id = o.application_id
left join rc on rc.offer_id = o.offer_id
