{#- What happened at the end of each fixed-rate period: retained by product transfer, redeemed, or reverted. -#}
with pt as (
    select * from {{ ref('stg_product_transfers') }}
),
lb as (
    select loan_id, completion_id, partner_id, min(snapshot_month) as first_month
    from {{ ref('stg_loan_book_monthly') }} group by 1, 2, 3
),
c as (
    select completion_id, product_id as original_product_id, loan_amount, product_range, property_type, region, borrower_type
    from {{ ref('fct_completions') }}
)
select
    pt.product_transfer_id,
    pt.loan_id,
    c.completion_id,
    lb.partner_id,
    pt.maturity_date,
    {{ month_start('pt.maturity_date') }}                as maturity_month,
    pt.decided_at,
    pt.outcome,
    pt.outcome = 'product_transfer'                      as is_retained,
    pt.new_product_id,
    pt.new_rate_card_id,
    c.original_product_id,
    c.loan_amount,
    c.product_range,
    c.property_type,
    c.region,
    c.borrower_type
from pt
left join lb on lb.loan_id = pt.loan_id
left join c  on c.completion_id = lb.completion_id
