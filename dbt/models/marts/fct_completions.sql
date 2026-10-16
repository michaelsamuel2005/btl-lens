{#- One row per completed loan: gross lending, the product and the funding partner it was allocated to. -#}
with c as (
    select * from {{ ref('stg_completions') }}
),
a as (
    select application_id, broker_id, borrower_type, property_type, purpose, region, portfolio_size, submitted_at
    from {{ ref('stg_applications') }}
),
al as (
    select completion_id, partner_id, allocation_id, allocation_month from {{ ref('stg_funding_allocations') }}
),
p as (
    select product_id, product_range, term_label, fee_pct from {{ ref('stg_products') }}
)
select
    c.completion_id,
    c.application_id,
    a.broker_id,
    c.product_id,
    p.product_range,
    p.term_label,
    al.partner_id,
    al.allocation_id,
    c.funds_released_at,
    cast(c.funds_released_at as date)                as completion_date,
    {{ month_start('c.funds_released_at') }}         as completion_month,
    a.submitted_at,
    {{ days_between('a.submitted_at', 'c.funds_released_at') }} as days_submission_to_completion,
    a.borrower_type,
    a.property_type,
    a.purpose,
    a.region,
    a.portfolio_size,
    c.loan_amount,
    c.market_value,
    round(100.0 * c.loan_amount / nullif(c.market_value, 0), 1) as ltv_at_completion_pct,
    c.monthly_rent,
    c.initial_rate_pct,
    c.fixed_years,
    c.term_type,
    c.completion_fee_gbp,
    p.fee_pct
from c
join a  on a.application_id = c.application_id
left join al on al.completion_id = c.completion_id
left join p  on p.product_id = c.product_id
