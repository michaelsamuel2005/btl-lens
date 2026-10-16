{#- The payload is JSON (a JSON column on DuckDB, VARIANT on Snowflake, jsonb on PostgreSQL); the json_get
    macro extracts the fields each warehouse's way. -#}
with src as (select * from {{ source('raw', 'portal_events') }})
select
    cast(event_id as varchar)                       as event_id,
    cast(event_type as varchar)                     as event_type,
    cast(event_at as timestamp)                     as event_at,
    cast(broker_id as varchar)                      as broker_id,
    cast(dip_id as varchar)                         as dip_id,
    cast(application_id as varchar)                 as application_id,
    cast({{ json_get('payload', 'session_id') }} as varchar)            as session_id,
    cast({{ json_get('payload', 'device') }} as varchar)                as device,
    cast({{ json_get('payload', 'feature_flags.instant_avm') }} as boolean) as instant_avm_flag,
    cast({{ json_get('payload', 'result') }} as varchar)                as dip_result,
    cast({{ json_get('payload', 'documents') }} as integer)             as documents_uploaded
from src
