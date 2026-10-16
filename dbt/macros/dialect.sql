{#- Cross-database helpers. Each macro dispatches on the adapter so the same models run on DuckDB (local),
    Snowflake (the trial) and PostgreSQL (for Lightdash). -#}

{% macro json_get(column, path) -%}
  {{ return(adapter.dispatch('json_get', 'btl_lens')(column, path)) }}
{%- endmacro %}

{% macro default__json_get(column, path) -%}
  json_extract_string({{ column }}, '$.{{ path }}')
{%- endmacro %}

{% macro duckdb__json_get(column, path) -%}
  json_extract_string({{ column }}, '$.{{ path }}')
{%- endmacro %}

{% macro snowflake__json_get(column, path) -%}
  ({{ column }}:{{ path }})::string
{%- endmacro %}

{% macro postgres__json_get(column, path) -%}
  ({{ column }} #>> '{{ "{" ~ path.replace('.', ',') ~ "}" }}')
{%- endmacro %}


{% macro days_between(start_ts, end_ts) -%}
  {{ return(adapter.dispatch('days_between', 'btl_lens')(start_ts, end_ts)) }}
{%- endmacro %}

{% macro default__days_between(start_ts, end_ts) -%}
  cast(date_diff('second', {{ start_ts }}, {{ end_ts }}) / 86400.0 as double)
{%- endmacro %}

{% macro snowflake__days_between(start_ts, end_ts) -%}
  cast(datediff('second', {{ start_ts }}, {{ end_ts }}) / 86400.0 as float)
{%- endmacro %}

{% macro postgres__days_between(start_ts, end_ts) -%}
  cast(extract(epoch from ({{ end_ts }} - {{ start_ts }})) / 86400.0 as double precision)
{%- endmacro %}


{% macro month_start(d) -%}
  cast(date_trunc('month', {{ d }}) as date)
{%- endmacro %}


{% macro regex_matches(column, pattern) -%}
  {{ return(adapter.dispatch('regex_matches', 'btl_lens')(column, pattern)) }}
{%- endmacro %}

{% macro default__regex_matches(column, pattern) -%}
  regexp_matches({{ column }}, '{{ pattern }}')
{%- endmacro %}

{% macro snowflake__regex_matches(column, pattern) -%}
  regexp_like({{ column }}, '.*{{ pattern }}.*')
{%- endmacro %}

{% macro postgres__regex_matches(column, pattern) -%}
  ({{ column }} ~ '{{ pattern }}')
{%- endmacro %}


{% macro median_of(column) -%}
  {{ return(adapter.dispatch('median_of', 'btl_lens')(column)) }}
{%- endmacro %}

{% macro default__median_of(column) -%}
  median({{ column }})
{%- endmacro %}

{% macro postgres__median_of(column) -%}
  percentile_cont(0.5) within group (order by {{ column }})
{%- endmacro %}


{#- round(x, n) on a float: PostgreSQL only has round(numeric, int), so it rounds through numeric there. -#}
{% macro round_to(column, digits) -%}
  {{ return(adapter.dispatch('round_to', 'btl_lens')(column, digits)) }}
{%- endmacro %}

{% macro default__round_to(column, digits) -%}
  round(cast({{ column }} as {{ btl_lens.type_double() }}), {{ digits }})
{%- endmacro %}

{% macro postgres__round_to(column, digits) -%}
  cast(round(cast({{ column }} as numeric), {{ digits }}) as {{ btl_lens.type_double() }})
{%- endmacro %}


{#- A 64-bit float type name that every target accepts (dbt.type_float() is 32-bit on DuckDB). -#}
{% macro type_double() -%}
  {{ return(adapter.dispatch('type_double', 'btl_lens')()) }}
{%- endmacro %}

{% macro default__type_double() -%}double{%- endmacro %}

{% macro postgres__type_double() -%}double precision{%- endmacro %}
