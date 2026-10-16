select
    b.broker_id,
    b.firm_name,
    b.network,
    case when b.network = 'Directly authorised' then 'Directly authorised' else 'Network member' end as authorisation,
    b.region,
    b.onboarded_date,
    b.fca_firm_ref
from {{ ref('stg_brokers') }} b
