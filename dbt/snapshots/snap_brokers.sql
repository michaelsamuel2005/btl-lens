{% snapshot snap_brokers %}
{#- Brokers move between networks and change names; this keeps every version with the dates it was valid.
    dim_broker shows the current version; the snapshot answers "which network was this broker in when the case
    completed". -#}
{{ config(target_schema='snapshots', unique_key='broker_id', strategy='check', check_cols=['firm_name', 'network', 'region']) }}
select * from {{ source('raw', 'brokers') }}
{% endsnapshot %}
