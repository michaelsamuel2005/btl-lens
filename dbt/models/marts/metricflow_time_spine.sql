{{ config(materialized='table') }}
-- Time spine for the dbt semantic layer (MetricFlow).
select date_day from {{ ref('dim_date') }}
