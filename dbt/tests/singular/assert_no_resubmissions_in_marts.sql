-- Broker resubmissions are flagged in staging and must never reach the application mart.
select f.application_id
from {{ ref('fct_applications') }} f
join {{ ref('stg_applications') }} s on s.application_id = f.application_id
where s.is_resubmission
