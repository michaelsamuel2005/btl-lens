{#- Every data-quality issue the pipeline detects in the source extracts, one row per record, so the marts can
    exclude or correct them and the scorecard can compare them with the planted answer key. -#}
with apps as (
    select * from {{ ref('stg_applications') }}
),
funnel as (
    select * from {{ ref('int_application_funnel') }}
),

duplicate_application as (
    select
        'duplicate_application' as issue_type, 'applications' as entity, application_id as record_id,
        'resubmission of ' || resubmission_of_application_id || ' within three days; excluded from the marts' as detail
    from apps where is_resubmission
),

status_out_of_order as (
    select
        'status_out_of_order', 'application_status_history', application_id,
        'valuation_received is stamped before valuation_instructed'
    from funnel where not status_order_valid
),

completion_date_mismatch as (
    -- the exported completed_at is not the date funds were released, or is set with no completion on record
    select
        'completion_date_mismatch', 'applications', a.application_id,
        case when c.completion_id is null
             then 'applications.completed_at (' || cast(a.completed_at_as_exported as varchar) || ') is set but no funds have been released'
             else 'applications.completed_at (' || cast(a.completed_at_as_exported as varchar) || ') differs from funds released ('
                  || cast(c.funds_released_at as varchar) || '); the marts use funds released' end
    from apps a
    left join {{ ref('stg_completions') }} c on c.application_id = a.application_id
    where a.completed_at_as_exported is not null
      and (c.completion_id is null
           or abs({{ days_between('a.completed_at_as_exported', 'c.funds_released_at') }}) > (1.0 / 24))
),

rent_basis_net as (
    select
        'rent_basis_net', 'applications', a.application_id,
        'broker network ' || b.network || ' declares rent systematically below the valuer''s gross rent (median ratio '
            || cast(n.median_declared_to_assessed as varchar) || '); policy uses the valuer''s figure'
    from apps a
    join {{ ref('stg_brokers') }} b on b.broker_id = a.broker_id
    join {{ ref('dq_rent_basis_by_network') }} n on n.network = b.network and n.rent_basis_suspect
    where not a.is_resubmission
),

stale_rate_card as (
    select
        'stale_rate_card', 'offers', o.offer_id,
        'offer priced on ' || o.rate_card_id || '; the card live at submission was ' || x.rate_card_id_expected
    from {{ ref('stg_offers') }} o
    join {{ ref('int_rate_card_at_submission') }} x on x.application_id = o.application_id
    where o.rate_card_id <> x.rate_card_id_expected
),

avm_ineligible as (
    select
        'avm_ineligible', 'valuations', v.valuation_id,
        'automated valuation outside AVM policy: ' || a.property_type || ' at '
            || cast(round(100.0 * a.loan_amount / nullif(a.property_value, 0), 1) as varchar) || '% LTV'
    from {{ ref('stg_valuations') }} v
    join apps a on a.application_id = v.application_id
    where v.valuation_type = 'avm'
      and a.purpose <> 'product_transfer'
      and (a.property_type = 'mufb_small' or 100.0 * a.loan_amount / nullif(a.property_value, 0) > {{ var('feature_max_ltv_pct') }})
),

partner_over_capacity as (
    -- allocations that took a partner past its monthly line, in the order the loans completed
    select 'partner_over_capacity', 'funding_allocations', allocation_id,
           partner_id || ' allocated ' || cast(round(running_total) as varchar) || ' against a line of ' || cast(round(monthly_capacity_gbp) as varchar)
               || ' in ' || cast(allocation_month as varchar)
    from (
        select
            al.allocation_id, al.partner_id, al.allocation_month, fp.monthly_capacity_gbp,
            sum(al.allocated_amount) over (partition by al.partner_id, al.allocation_month
                                           order by c.funds_released_at, al.allocation_id
                                           rows between unbounded preceding and current row) as running_total
        from {{ ref('stg_funding_allocations') }} al
        join {{ ref('stg_completions') }} c on c.completion_id = al.completion_id
        join {{ ref('stg_funding_partners') }} fp on fp.partner_id = al.partner_id
    ) t
    where running_total > monthly_capacity_gbp
),

pii_in_notes as (
    select
        'pii_in_notes', 'applications', application_id,
        'free-text notes contain a personal name; the marts do not carry the notes column'
    from apps
    where notes is not null and {{ regex_matches('notes', "(Mr|Mrs|Ms|Miss|Dr)\\.? [A-Z][a-z]+ [A-Z][a-z]+") }}
),

orphan_broker as (
    select
        'orphan_broker', 'applications', a.application_id,
        'broker_id ' || a.broker_id || ' is not in the broker file'
    from apps a
    left join {{ ref('stg_brokers') }} b on b.broker_id = a.broker_id
    where b.broker_id is null
),

nonpositive_loan as (
    select
        'nonpositive_loan', 'applications', application_id,
        'loan amount ' || cast(loan_amount as varchar) || ' is not positive; quarantined from the marts'
    from apps where loan_amount <= 0
),

rental_cover_below_policy as (
    -- a consequence check: at the rate the offer actually carries, policy rental cover is not met
    select
        'rental_cover_below_policy', 'offers', offer_id,
        'rental cover ' || cast(rental_cover_policy_pct as varchar) || '% at the offered rate of ' || cast(initial_rate_pct as varchar)
            || '% is below the ' || cast(min_rental_cover_pct as varchar) || '% minimum'
    from {{ ref('int_rental_cover') }}
    where not rental_cover_passes
)

select * from duplicate_application
union all select * from status_out_of_order
union all select * from completion_date_mismatch
union all select * from rent_basis_net
union all select * from stale_rate_card
union all select * from avm_ineligible
union all select * from partner_over_capacity
union all select * from pii_in_notes
union all select * from orphan_broker
union all select * from nonpositive_loan
union all select * from rental_cover_below_policy
