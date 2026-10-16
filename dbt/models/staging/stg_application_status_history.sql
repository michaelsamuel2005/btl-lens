with src as (select * from {{ source('raw', 'application_status_history') }})
select
    cast(application_id as varchar)                 as application_id,
    cast(status as varchar)                         as status,
    cast(status_at as timestamp)                    as status_at
from src
