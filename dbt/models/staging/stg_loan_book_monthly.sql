with src as (select * from {{ source('raw', 'loan_book_monthly') }})
select
    cast(snapshot_month as date)                    as snapshot_month,
    cast(loan_id as varchar)                        as loan_id,
    cast(completion_id as varchar)                  as completion_id,
    cast(partner_id as varchar)                     as partner_id,
    cast(status as varchar)                         as loan_status,
    cast(balance as decimal(14, 2))                 as balance,
    cast(indexed_value as decimal(14, 2))           as indexed_value,
    cast(ltv_current_pct as decimal(5, 1))          as ltv_current_pct,
    cast(monthly_rent as decimal(10, 2))            as monthly_rent,
    cast(pay_rate_pct as decimal(5, 2))             as pay_rate_pct,
    cast(rental_cover_current_pct as decimal(6, 1)) as rental_cover_current_pct,
    cast(arrears_months as integer)                 as arrears_months,
    cast(fixed_end_date as date)                    as fixed_end_date
from src
