{#- One row per genuine application, with its funnel timings and outcome. Broker resubmissions are removed, and
    records that fail hard validation (a loan amount that is not positive) are quarantined: both are listed in
    dq_issues. Where the status history is out of order, the valuation timestamps are nulled rather than guessed. -#}
with a as (
    select * from {{ ref('stg_applications') }}
    where not is_resubmission
      and loan_amount > 0
),
f as (
    select * from {{ ref('int_application_funnel') }}
),
v as (
    select * from {{ ref('stg_valuations') }}
),
e as (
    select * from {{ ref('int_feature_eligibility') }}
),
o as (
    select application_id, offer_id, loan_amount as offered_loan_amount, ltv_pct as offered_ltv_pct from {{ ref('stg_offers') }}
),
rc as (
    select * from {{ ref('int_rental_cover') }}
),
c as (
    select application_id, completion_id, funds_released_at from {{ ref('stg_completions') }}
),
lb as (
    select ltv_band, ltv_from_pct, ltv_to_pct from {{ ref('ltv_bands') }}
)
select
    a.application_id,
    a.dip_id,
    a.broker_id,
    a.product_id,
    a.submitted_at,
    cast(a.submitted_at as date)                     as submitted_date,
    {{ month_start('a.submitted_at') }}              as submitted_month,
    a.borrower_type,
    a.tax_band,
    a.property_type,
    a.purpose,
    a.region,
    a.postcode_area,
    a.portfolio_size,
    a.portfolio_size >= 4                            as is_portfolio_landlord,
    a.property_value,
    a.loan_amount,
    round(100.0 * a.loan_amount / nullif(a.property_value, 0), 1) as ltv_at_application_pct,
    lb.ltv_band                                      as ltv_band_at_application,
    a.declared_monthly_rent,
    v.monthly_rent_assessed,
    v.market_value                                   as valuation_market_value,
    v.valuation_type,
    f.outcome,
    f.outcome = 'completed'                          as is_completed,
    f.outcome = 'withdrawn'                          as is_withdrawn,
    f.outcome = 'declined'                           as is_declined,
    f.offered_at is not null                         as reached_offer,
    case when f.status_order_valid then f.valuation_instructed_at end as valuation_instructed_at,
    case when f.status_order_valid then f.valuation_received_at end   as valuation_received_at,
    f.underwriting_started_at,
    f.offered_at,
    f.offer_accepted_at,
    f.completed_at,                                  -- from the status history (funds released)
    f.declined_at,
    f.withdrawn_at,
    case when f.status_order_valid then f.valuation_days end   as valuation_days,   -- nulled when the history is out of order
    f.underwriting_days,
    f.days_to_offer,
    f.days_offer_to_completion,
    f.days_to_completion,
    f.status_order_valid,
    o.offer_id,
    o.offered_loan_amount,
    o.offered_ltv_pct,
    rc.rental_cover_policy_pct,
    rc.rental_cover_passes,
    rc.min_rental_cover_pct,
    rc.declared_to_assessed_rent_ratio,
    c.completion_id,
    e.feature_eligible,
    e.is_post_launch,
    e.avm_used
from a
left join f  on f.application_id = a.application_id
left join v  on v.application_id = a.application_id
left join e  on e.application_id = a.application_id
left join o  on o.application_id = a.application_id
left join rc on rc.application_id = a.application_id
left join c  on c.application_id = a.application_id
left join lb on round(100.0 * a.loan_amount / nullif(a.property_value, 0), 1) > lb.ltv_from_pct
            and round(100.0 * a.loan_amount / nullif(a.property_value, 0), 1) <= lb.ltv_to_pct
