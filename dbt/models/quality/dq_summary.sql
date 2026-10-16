select
    issue_type,
    entity,
    count(*) as issues
from {{ ref('dq_issues') }}
group by issue_type, entity
order by issues desc
