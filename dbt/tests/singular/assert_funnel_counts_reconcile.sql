-- Completed applications in the mart equal the completions file, less resubmissions (which never complete).
with m as (select count(*) as n from {{ ref('fct_applications') }} where is_completed),
     c as (select count(*) as n from {{ ref('stg_completions') }})
select m.n as mart_completed, c.n as completions_file
from m, c
where m.n <> c.n
