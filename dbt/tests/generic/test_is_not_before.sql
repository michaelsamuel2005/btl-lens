{% test is_not_before(model, column_name, compare_column) %}
{#- Fails for rows where column_name is earlier than compare_column (both populated). -#}
select *
from {{ model }}
where {{ column_name }} is not null
  and {{ compare_column }} is not null
  and {{ column_name }} < {{ compare_column }}
{% endtest %}
