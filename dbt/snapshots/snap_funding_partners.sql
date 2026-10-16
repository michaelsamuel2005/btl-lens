{% snapshot snap_funding_partners %}
{#- Funding lines are renegotiated; capacity and end dates change. Kept as slowly changing dimension type 2. -#}
{{ config(target_schema='snapshots', unique_key='partner_id', strategy='check', check_cols=['monthly_capacity_gbp', 'line_end', 'scope']) }}
select * from {{ source('raw', 'funding_partners') }}
{% endsnapshot %}
