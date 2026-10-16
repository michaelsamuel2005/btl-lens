select
    partner_id,
    partner_name,
    line_start,
    line_end,
    line_end is null                                     as line_is_open,
    monthly_capacity_gbp,
    case scope
        when 'all' then 'All products'
        when 'core_only' then 'Core range only'
        when 'standard_75' then 'Standard property up to 75% LTV'
    end                                                  as scope_description
from {{ ref('stg_funding_partners') }}
