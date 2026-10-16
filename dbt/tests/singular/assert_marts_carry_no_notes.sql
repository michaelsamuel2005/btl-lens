-- The free-text notes column can contain personal data and is not carried into any mart.
{% set cols = adapter.get_columns_in_relation(ref('fct_applications')) | map(attribute='name') | map('lower') | list %}
select 'fct_applications carries a notes column' as failure
where {{ 'notes' in cols }}
