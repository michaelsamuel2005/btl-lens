with src as (select * from {{ source('raw', 'brokers') }})
select
    cast(broker_id as varchar)                      as broker_id,
    cast(firm_name as varchar)                      as firm_name,
    cast(network as varchar)                        as network,
    cast(region as varchar)                         as region,
    cast(onboarded_date as date)                    as onboarded_date,
    cast(fca_firm_ref as integer)                   as fca_firm_ref
from src
