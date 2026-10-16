select
    product_id,
    product_range,
    property_scope,
    borrower_scope,
    term_type,
    fixed_years,
    term_label,
    max_ltv_pct,
    fee_pct,
    purposes,
    case when purposes = 'product_transfer' then 'Product transfer' else 'Purchase and remortgage' end as purpose_group,
    erc_applies
from {{ ref('stg_products') }}
