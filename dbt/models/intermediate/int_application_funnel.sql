{#- One row per application with the timestamp of each stage it reached, and the days between stages.
    Status history is the only source of timing; applications.completed_at is not trusted (see dq_issues). -#}
with h as (
    select * from {{ ref('stg_application_status_history') }}
),

stages as (
    select
        application_id,
        min(case when status = 'submitted'             then status_at end) as submitted_at,
        min(case when status = 'valuation_instructed'  then status_at end) as valuation_instructed_at,
        min(case when status = 'valuation_received'    then status_at end) as valuation_received_at,
        min(case when status = 'underwriting_started'  then status_at end) as underwriting_started_at,
        min(case when status = 'offered'               then status_at end) as offered_at,
        min(case when status = 'offer_accepted'        then status_at end) as offer_accepted_at,
        min(case when status = 'completed'             then status_at end) as completed_at,
        min(case when status = 'declined'              then status_at end) as declined_at,
        min(case when status = 'withdrawn'             then status_at end) as withdrawn_at,
        count(*)                                                             as status_rows
    from h
    group by application_id
)

select
    *,
    {{ days_between('valuation_instructed_at', 'valuation_received_at') }}  as valuation_days,
    {{ days_between('valuation_received_at', 'offered_at') }}               as underwriting_days,
    {{ days_between('submitted_at', 'offered_at') }}                        as days_to_offer,
    {{ days_between('offer_accepted_at', 'completed_at') }}                 as days_offer_to_completion,
    {{ days_between('submitted_at', 'completed_at') }}                      as days_to_completion,
    case
        when completed_at is not null then 'completed'
        when declined_at  is not null then 'declined'
        when withdrawn_at is not null then 'withdrawn'
        when offer_accepted_at is not null then 'offer accepted'
        when offered_at   is not null then 'offered'
        when underwriting_started_at is not null then 'underwriting'
        when valuation_received_at is not null then 'valuation received'
        when valuation_instructed_at is not null then 'valuation instructed'
        else 'submitted'
    end                                                                     as outcome,
    case when valuation_received_at < valuation_instructed_at then false else true end as status_order_valid
from stages
