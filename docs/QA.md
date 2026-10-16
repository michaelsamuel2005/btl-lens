# How the data is checked

Seven layers, each catching a different kind of mistake. The numbers below are from the full-size run
(`python run.py`); `outputs/scorecard.md` and `dbt/target/run_results.json` hold the live values.

| Layer | What it checks | Where | Result |
|---|---|---|---|
| Source tests | Keys unique and present, relationships between files, value ranges, accepted values. Planted defects trip a few of these on purpose, at `warn` severity so the load continues and the finding is recorded. | `models/staging/sources.yml` | 14 sources |
| Model tests | `unique`, `not_null`, `relationships`, `accepted_values` and `dbt_utils` ranges and combinations on staging, intermediate and mart keys and measures. | `*.yml` beside each layer | with the source, custom and singular tests: 139 data tests, 135 pass, 4 warn |
| Custom tests | `is_not_before` (a date must not precede another, used on the offer and valuation dates) and `at_least_column` (a measure must meet a policy column, used on rental cover). Written as generic tests so they are reused. | `tests/generic/` | pass or warn as designed |
| Singular tests | Reconciliations: every completion is allocated once for its full amount; funnel counts agree with the completions file; no resubmissions and no free-text notes reach a mart. | `tests/singular/` | 4 of 4 pass |
| Unit tests | The logic of two models against hand-calculated rows, with no data needed: days to offer from a status history, and policy rental cover with stress rates. | `models/intermediate/intermediate.yml` | 2 of 2 pass |
| Answer-key scorecard | The simulator plants known defects. The data-quality layer never sees the answer key; `analysis/scorecard.py` compares what it found with what was planted. | `analysis/scorecard.py` | 2,467 of 2,467 caught, 0 false alarms, 10 of 10 defect types |
| Python tests | The simulator: policy formulas (stress rate, rental cover), the rate path and house-price index, determinism for a fixed seed, every planted defect names a real record, the feature effect is recorded. The pipeline: a quarter-size run end to end (build passes with only the expected warnings, the scorecard catches everything, unit tests and snapshots ran, the impact estimate covers the designed effect), and the marts' SQL never mentions the answer key. | `tests/` | 12 of 12 pass |

The four warnings in a normal run are expected: two source-level monitors that the planted defects trip (a
non-positive loan amount, and broker ids that are not in the broker file) and two consequence checks on offers
(rental cover below the policy minimum, at the rate the offer actually carries). They are warnings because the
pipeline is meant to keep going and report, not stop.

## What the data-quality register holds

`quality.dq_issues` has one row per problem record: the issue type, the entity, the record id and a sentence saying
what is wrong and what the marts do about it. `quality.dq_summary` counts them by type for a dashboard tile.

| Issue | Records | What the marts do |
|---|---:|---|
| `completion_date_mismatch` | 1,017 | Use the date funds were released, not the exported `completed_at` |
| `rent_basis_net` | 892 | One broker network declares rent net of a fee; policy uses the valuer's gross rent |
| `duplicate_application` | 230 | Exclude resubmissions (same DIP and broker within three days) |
| `stale_rate_card` | 112 | Flag offers not priced on the rate card live at submission |
| `status_out_of_order` | 91 | Null the valuation timing that depends on the swapped timestamps |
| `pii_in_notes` | 50 | The notes column is not carried into any mart (tested) |
| `avm_ineligible` | 30 | Register only; the feature-impact note counts them as a policy question |
| `orphan_broker` | 20 | Keep the application; its broker id has no row in the broker dimension (documented on the column) |
| `partner_over_capacity` | 15 | Show utilisation above 100% and list the allocations |
| `nonpositive_loan` | 10 | Quarantine from the marts |
| `rental_cover_below_policy` | 4 | Found, not planted: follows from other defects. Flag only |

## Two things this check does not prove

The scorecard shows the detection rules match the defects the simulator knows about. Real data has defects nobody
planted, so a 100% score here is evidence that the rules work as specified, not that real data would be clean.

The numbers are from simulated data; no real lender's data, pricing or policy is used (see `docs/ASSUMPTIONS.md`).

## Cross-warehouse check

The same project builds on DuckDB and PostgreSQL with identical results: 177 checks pass, 4 warn, 0 error on each,
and the issue counts, gross lending, application counts and loan-book arrears counts match between the two. The
Snowflake target is written (adapter macros, loader, profile) but has not been run; see `docs/SNOWFLAKE.md`.

## Known limits

- The status history is derived from timestamps in the simulator; real exports have more states and reversals.
- Rental cover uses the valuer's gross rent and a single stress rate rule; real policy has more branches (HMO
  rent bases, top-slicing, portfolio rules).
- Censoring for the impact analysis uses a fixed 60-day window rather than modelling time to event.
