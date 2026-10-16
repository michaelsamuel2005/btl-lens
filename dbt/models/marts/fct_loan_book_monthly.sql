{#- Month-end loan book with reporting bands. Grain: loan x month. -#}
with s as (
    select * from {{ ref('stg_loan_book_monthly') }}
),
c as (
    select completion_id, product_id, product_range, property_type, purpose, region, borrower_type, completion_date
    from {{ ref('fct_completions') }}
),
lb as (
    select * from {{ ref('ltv_bands') }}
),
ab as (
    select * from {{ ref('arrears_buckets') }}
)
select
    s.snapshot_month,
    s.loan_id,
    s.completion_id,
    s.partner_id,
    c.product_id,
    c.product_range,
    c.property_type,
    c.purpose,
    c.region,
    c.borrower_type,
    c.completion_date,
    s.loan_status,
    s.balance,
    s.indexed_value,
    s.ltv_current_pct,
    lb.ltv_band,
    s.monthly_rent,
    s.pay_rate_pct,
    s.rental_cover_current_pct,
    s.rental_cover_current_pct < 125                     as rental_cover_below_125,
    s.arrears_months,
    ab.arrears_bucket,
    s.arrears_months >= 3                                as is_in_arrears_3_plus,
    s.fixed_end_date,
    s.fixed_end_date <= s.snapshot_month + interval '6 months' as maturing_within_6_months
from s
left join c  on c.completion_id = s.completion_id
left join lb on s.ltv_current_pct > lb.ltv_from_pct and s.ltv_current_pct <= lb.ltv_to_pct
left join ab on s.arrears_months between ab.arrears_months_from and ab.arrears_months_to
