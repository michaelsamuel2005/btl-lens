{{ config(materialized='table') }}
with spine as (
    {{ dbt_utils.date_spine(datepart="day", start_date="cast('2023-01-01' as date)", end_date="cast('2027-01-01' as date)") }}
)
select
    cast(date_day as date)                              as date_day,
    extract(year from date_day)                         as year,
    extract(quarter from date_day)                      as quarter,
    extract(month from date_day)                        as month,
    {{ month_start('date_day') }}                       as month_start,
    cast(extract(year from date_day) as varchar) || '-' ||
        lpad(cast(extract(month from date_day) as varchar), 2, '0') as year_month,
    extract(dow from date_day) in (0, 6)                as is_weekend
from spine
