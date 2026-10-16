{#- Difference-in-differences on the feature analysis set: one row for the eligible group, one for the ineligible
    comparison group, and one for the difference between their changes. The Python analysis adds confidence
    intervals; this gives the same point estimates in SQL for dashboards. -#}
with cells as (
    select
        analysis_group,
        period,
        count(*)                                                   as applications,
        avg(case when avm_used then 1.0 else 0.0 end)              as avm_share,
        avg(days_to_offer)                                         as mean_days_to_offer,
        avg(case when is_withdrawn then 1.0 else 0.0 end)          as withdrawal_rate
    from {{ ref('fct_feature_impact') }}
    group by analysis_group, period
),
wide as (
    select
        analysis_group,
        max(case when period = 'pre-launch'  then applications end)       as applications_pre,
        max(case when period = 'post-launch' then applications end)       as applications_post,
        max(case when period = 'post-launch' then avm_share end)          as avm_share_post,
        max(case when period = 'pre-launch'  then mean_days_to_offer end) as days_to_offer_pre,
        max(case when period = 'post-launch' then mean_days_to_offer end) as days_to_offer_post,
        max(case when period = 'pre-launch'  then withdrawal_rate end)    as withdrawal_rate_pre,
        max(case when period = 'post-launch' then withdrawal_rate end)    as withdrawal_rate_post
    from cells
    group by analysis_group
),
changes as (
    select
        *,
        days_to_offer_post - days_to_offer_pre       as days_to_offer_change,
        withdrawal_rate_post - withdrawal_rate_pre   as withdrawal_rate_change
    from wide
),
did as (
    select
        'difference-in-differences'                                                             as analysis_group,
        null                                                                                    as applications_pre,
        null                                                                                    as applications_post,
        null                                                                                    as avm_share_post,
        null                                                                                    as days_to_offer_pre,
        null                                                                                    as days_to_offer_post,
        null                                                                                    as withdrawal_rate_pre,
        null                                                                                    as withdrawal_rate_post,
        max(case when analysis_group = 'eligible' then days_to_offer_change end)
            - max(case when analysis_group = 'ineligible' then days_to_offer_change end)        as days_to_offer_change,
        max(case when analysis_group = 'eligible' then withdrawal_rate_change end)
            - max(case when analysis_group = 'ineligible' then withdrawal_rate_change end)      as withdrawal_rate_change
    from changes
)
select
    analysis_group,
    cast(applications_pre as integer)                 as applications_pre,
    cast(applications_post as integer)                as applications_post,
    {{ round_to('avm_share_post', 3) }}          as avm_share_post,
    {{ round_to('days_to_offer_pre', 2) }}       as days_to_offer_pre,
    {{ round_to('days_to_offer_post', 2) }}      as days_to_offer_post,
    {{ round_to('days_to_offer_change', 2) }}    as days_to_offer_change,
    {{ round_to('withdrawal_rate_pre', 4) }}     as withdrawal_rate_pre,
    {{ round_to('withdrawal_rate_post', 4) }}    as withdrawal_rate_post,
    {{ round_to('withdrawal_rate_change', 4) }}  as withdrawal_rate_change
from changes
union all
select
    analysis_group,
    cast(applications_pre as integer), cast(applications_post as integer), cast(avm_share_post as {{ btl_lens.type_double() }}),
    cast(days_to_offer_pre as {{ btl_lens.type_double() }}), cast(days_to_offer_post as {{ btl_lens.type_double() }}), {{ round_to('days_to_offer_change', 2) }},
    cast(withdrawal_rate_pre as {{ btl_lens.type_double() }}), cast(withdrawal_rate_post as {{ btl_lens.type_double() }}), {{ round_to('withdrawal_rate_change', 4) }}
from did
