with src as (select * from {{ source('raw', 'product_transfers') }})
select
    cast(product_transfer_id as varchar)            as product_transfer_id,
    cast(loan_id as varchar)                        as loan_id,
    cast(maturity_date as date)                     as maturity_date,
    cast(outcome as varchar)                        as outcome,
    cast(decided_at as date)                        as decided_at,
    cast(new_product_id as varchar)                 as new_product_id,
    cast(new_rate_card_id as varchar)               as new_rate_card_id
from src
