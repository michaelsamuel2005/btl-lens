{#- The analysis set for the instant AVM remortgage launch: remortgage applications with enough time to reach an
    outcome, their eligibility, period and timings. Cases submitted within the censoring window before the latest
    data are excluded, because slow cases among them would not yet have an offer and the means would be biased. -#}
with a as (
    select * from {{ ref('fct_applications') }}
),
latest as (
    select max(submitted_at) as latest_submitted_at from a
)
select
    a.application_id,
    a.submitted_at,
    a.submitted_month,
    a.feature_eligible,
    a.is_post_launch,
    case when a.feature_eligible then 'eligible' else 'ineligible' end as analysis_group,
    case when a.is_post_launch then 'post-launch' else 'pre-launch' end as period,
    a.avm_used,
    a.valuation_type,
    a.reached_offer,
    a.is_withdrawn,
    a.is_completed,
    a.valuation_days,
    a.underwriting_days,
    a.days_to_offer,
    a.property_type,
    a.ltv_at_application_pct,
    a.portfolio_size
from a
cross join latest
where a.purpose = 'remortgage'
  and a.submitted_at <= latest.latest_submitted_at - interval '{{ var("analysis_censoring_days") }} days'
