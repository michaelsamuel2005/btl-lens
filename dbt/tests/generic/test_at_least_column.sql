{% test at_least_column(model, column_name, threshold_column) %}
{#- Fails for rows where column_name is below threshold_column (both populated), e.g. rental cover against policy. -#}
select *
from {{ model }}
where {{ column_name }} is not null
  and {{ threshold_column }} is not null
  and {{ column_name }} < {{ threshold_column }}
{% endtest %}
