-- Every completed loan is allocated to exactly one funding partner for its full amount, and the totals agree.
with c as (select sum(loan_amount) as total, count(*) as n from {{ ref('fct_completions') }}),
     a as (select sum(allocated_amount) as total, count(*) as n from {{ ref('stg_funding_allocations') }})
select c.total as completions_total, a.total as allocations_total, c.n as completions, a.n as allocations
from c, a
where abs(c.total - a.total) > 0.01 or c.n <> a.n
