{#- A row-level threshold would flag noise: declared and assessed rents differ by a few percent on every case.
    A systematic problem shows up where it was introduced, so the test is at network level: the median ratio of
    declared to assessed rent across a network's applications. -#}
with r as (
    select
        a.application_id,
        a.broker_id,
        b.network,
        rc.declared_to_assessed_rent_ratio
    from {{ ref('stg_applications') }} a
    join {{ ref('int_rental_cover') }} rc on rc.application_id = a.application_id
    left join {{ ref('stg_brokers') }} b on b.broker_id = a.broker_id
    where not a.is_resubmission
)
select
    network,
    count(*)                                                        as applications,
    {{ round_to(median_of('declared_to_assessed_rent_ratio'), 3) }}  as median_declared_to_assessed,
    round(avg(declared_to_assessed_rent_ratio), 3)                  as mean_declared_to_assessed,
    count(*) >= 30 and {{ median_of('declared_to_assessed_rent_ratio') }} < 1 - {{ var('rent_basis_tolerance') }}
                                                                    as rent_basis_suspect
from r
group by network
