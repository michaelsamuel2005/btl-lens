{#- Recomputes rental cover for every offer from policy, independently of the figure the offer carries:
    the valuer's gross rent, the stress rate for the product's term, and the minimum for the borrower's tax band. -#}
with o as (
    select * from {{ ref('stg_offers') }}
),
a as (
    select application_id, tax_band, declared_monthly_rent, purpose, property_type, portfolio_size, property_value
    from {{ ref('stg_applications') }}
),
v as (
    select application_id, monthly_rent_assessed, market_value, valuation_type from {{ ref('stg_valuations') }}
),
p as (
    select product_id, term_type, fixed_years from {{ ref('stg_products') }}
),
pol as (
    select * from {{ ref('policy_rental_cover') }}
),
calc as (
    select
        o.offer_id,
        o.application_id,
        o.loan_amount,
        o.initial_rate_pct,
        p.term_type,
        p.fixed_years,
        v.monthly_rent_assessed,
        a.declared_monthly_rent,
        a.tax_band,
        pol.min_rental_cover_pct,
        -- stress rate: five-year fixes are stressed at the pay rate; shorter terms at max(pay rate + 2, 5.5)
        cast(case when p.term_type = 'fixed' and p.fixed_years >= 5 then o.initial_rate_pct
                  else greatest(o.initial_rate_pct + {{ var('stress_uplift_pct', 2.0) }}, {{ var('stress_floor_pct', 5.5) }}) end
             as decimal(6, 2))                                          as stress_rate_policy_pct,
        o.stress_rate_pct                                               as stress_rate_as_offered_pct
    from o
    join a   on a.application_id = o.application_id
    left join v on v.application_id = o.application_id
    join p   on p.product_id = o.product_id
    left join pol on pol.tax_band = a.tax_band
)
select
    *,
    round(100.0 * monthly_rent_assessed * 12 / (loan_amount * stress_rate_policy_pct / 100.0), 1)
                                                                        as rental_cover_policy_pct,
    round(100.0 * monthly_rent_assessed * 12 / (loan_amount * stress_rate_policy_pct / 100.0), 1) >= min_rental_cover_pct
                                                                        as rental_cover_passes,
    round(declared_monthly_rent / nullif(monthly_rent_assessed, 0), 3)  as declared_to_assessed_rent_ratio
from calc
