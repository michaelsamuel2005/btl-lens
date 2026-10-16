{#- Funding partner utilisation: what was allocated to each partner each month against its line. -#}
with al as (
    select
        partner_id,
        allocation_month,
        sum(allocated_amount)   as allocated_gbp,
        count(*)                as loans_allocated
    from {{ ref('stg_funding_allocations') }}
    group by partner_id, allocation_month
),
fp as (
    select * from {{ ref('stg_funding_partners') }}
)
select
    al.partner_id,
    fp.partner_name,
    al.allocation_month,
    al.loans_allocated,
    al.allocated_gbp,
    fp.monthly_capacity_gbp,
    round(100.0 * al.allocated_gbp / nullif(fp.monthly_capacity_gbp, 0), 1) as utilisation_pct,
    al.allocated_gbp > fp.monthly_capacity_gbp                              as is_over_line,
    al.allocated_gbp - fp.monthly_capacity_gbp                              as over_line_gbp,
    al.allocation_month < fp.line_start or al.allocation_month > coalesce(fp.line_end, cast('9999-12-31' as date))
                                                                            as is_outside_line_dates
from al
join fp on fp.partner_id = al.partner_id
