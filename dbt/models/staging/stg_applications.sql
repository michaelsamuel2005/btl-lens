{#- One row per application as submitted. Resubmissions are flagged here and excluded from the marts;
    the flag keeps the staging layer a faithful copy of the source. -#}
with src as (
    select * from {{ source('raw', 'applications') }}
),

typed as (
    select
        cast(application_id as varchar)             as application_id,
        cast(dip_id as varchar)                     as dip_id,
        cast(broker_id as varchar)                  as broker_id,
        cast(submitted_at as timestamp)             as submitted_at,
        cast(borrower_type as varchar)              as borrower_type,
        cast(tax_band as varchar)                   as tax_band,
        cast(property_type as varchar)              as property_type,
        cast(purpose as varchar)                    as purpose,
        cast(region as varchar)                     as region,
        cast(postcode_area as varchar)              as postcode_area,
        cast(portfolio_size as integer)             as portfolio_size,
        cast(property_value as decimal(14, 2))      as property_value,
        cast(loan_amount as decimal(14, 2))         as loan_amount,
        cast(declared_monthly_rent as decimal(10, 2)) as declared_monthly_rent,
        cast(product_id as varchar)                 as product_id,
        cast(rate_card_id as varchar)               as rate_card_id,
        cast(valuation_type_requested as varchar)   as valuation_type_requested,
        cast(notes as varchar)                      as notes,
        cast(status_current as varchar)             as status_current,
        cast(completed_at as timestamp)             as completed_at_as_exported
    from src
),

-- A resubmission is the same decision in principle submitted again by the same broker within three days.
ranked as (
    select
        *,
        row_number() over (partition by dip_id, broker_id order by submitted_at, application_id) as submission_rank,
        min(submitted_at) over (partition by dip_id, broker_id) as first_submitted_at,
        first_value(application_id) over (partition by dip_id, broker_id order by submitted_at, application_id) as first_application_id
    from typed
)

select
    application_id, dip_id, broker_id, submitted_at, borrower_type, tax_band, property_type, purpose, region,
    postcode_area, portfolio_size, property_value, loan_amount, declared_monthly_rent, product_id, rate_card_id,
    valuation_type_requested, notes, status_current, completed_at_as_exported,
    case when submission_rank > 1 and {{ days_between('first_submitted_at', 'submitted_at') }} <= 3
         then true else false end                   as is_resubmission,
    case when submission_rank > 1 and {{ days_between('first_submitted_at', 'submitted_at') }} <= 3
         then first_application_id end              as resubmission_of_application_id
from ranked
