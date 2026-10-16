{#- Which applications were eligible for the instant AVM remortgage option, whether they were submitted after its
    launch, and whether an AVM was actually used. Eligibility is derived from the application, never read from a flag. -#}
with a as (
    select * from {{ ref('stg_applications') }} where not is_resubmission
),
v as (
    select application_id, valuation_type from {{ ref('stg_valuations') }}
)
select
    a.application_id,
    a.purpose = 'remortgage'
        and a.property_type in ('standard', 'hmo_small')
        and 100.0 * a.loan_amount / nullif(a.property_value, 0) <= {{ var('feature_max_ltv_pct') }}
        and a.portfolio_size <= {{ var('feature_max_portfolio_size') }}        as feature_eligible,
    cast(a.submitted_at as date) >= cast('{{ var("feature_launch_date") }}' as date) as is_post_launch,
    coalesce(v.valuation_type = 'avm', false)                                 as avm_used
from a
left join v on v.application_id = a.application_id
