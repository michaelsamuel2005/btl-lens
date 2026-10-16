# btl-lens

A buy-to-let marketplace lender's analytics stack, built end to end on simulated data: raw extracts from the source
systems, a tested dbt project, a data-quality register that finds known problems, a post-launch evaluation of a
product feature, and the metadata that BI tools read.

It is a portfolio project. **The data is simulated**; nothing in it is a real lender's data, pricing or policy
(see `docs/ASSUMPTIONS.md`). Simulating the data is what makes the checking honest: the generator plants known
defects and a known feature effect, so the pipeline can be scored against an answer key it never reads.

## Results (full-size run, `python run.py`, about 90 seconds)

**Pipeline.** 51,427 decisions in principle become 15,363 genuine applications, 13,520 offers and 9,911 completions
(£2.40bn lent) across January 2023 to September 2026, with a 168,952-row monthly loan book. `dbt build` runs 35
models, 3 seeds, 2 snapshots, 139 data tests and 2 unit tests: 177 pass, 4 warn by design, 0 error. The same project
builds on PostgreSQL with identical results.

**Data quality.** Ten defect types were planted (duplicate resubmissions, swapped status timestamps, a wrong completion
date, one broker network declaring rent net of a fee, a stale rate card, automated valuations outside policy, a
funding line breached, names typed into notes, broker ids missing from the broker file, non-positive loans). The
data-quality layer found **2,467 of 2,467** planted records with **no false alarms**. This shows the rules match
the defects that were planted; real data has defects nobody planted (`docs/QA.md`).

**Feature evaluation.** "Instant AVM remortgage" launched on 6 April 2026, three months after a background
underwriting speed-up that helped every case. A before-and-after comparison credits the feature with 8.8 days; a difference-in-differences
against ineligible remortgages gives **7.4 days sooner to offer** (95% CI 6.7 to 8.0), which contains the 7.3 days
the simulation built in. The withdrawal estimate (7.7 points lower, CI 0.9 to 14.5) has a wide interval and is
reported as directional only. Full note: `docs/FEATURE_IMPACT.md`.

## Run it

```bash
pip install -r requirements.txt
python run.py                      # simulate -> dbt deps -> dbt build -> scorecard -> feature impact -> BI export
python run.py --scale 0.25         # quarter-size data (what CI runs)
python -m pytest -q                # 12 tests, including a quarter-size run end to end
```

Other warehouses: `python run.py --target postgres` (set `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`) loads the raw
files with `scripts/load_warehouse.py` and builds there. Snowflake is set up the same way but has not been run
(`docs/SNOWFLAKE.md`). Orchestration: `dagster dev -m orchestration.definitions` shows the asset graph (raw extracts,
every dbt model with its lineage, and the three analyses) and a daily schedule.

## What is in it

| Layer | What | Where |
|---|---|---|
| Simulator | Seeded generator of brokers, DIPs, applications, status history, valuations, offers, completions, funding allocations, loan book, product transfers and portal events, with planted defects and an answer key | `simulate/` |
| Staging | One view per source, typed and renamed, with source tests (severity `warn` where a defect is expected) | `dbt/models/staging/` |
| Intermediate | Funnel timings from the status history, recomputed rental cover and stress rates, rate card live at submission, feature eligibility | `dbt/models/intermediate/` |
| Marts | Star schema: five dimensions, facts for applications, offers, completions, funding, loan book, product transfers and the feature analysis set; a time spine | `dbt/models/marts/` |
| Quality | `dq_issues` (one row per problem record), `dq_summary`, and a network-level rent-basis test | `dbt/models/quality/` |
| Governance | One definition and owner per metric; exposures; dbt semantic layer (2 semantic models, 8 metrics); Lightdash metrics in YAML; docs `meta.owner` | `docs/METRICS.md`, `dbt/models/` |
| Analysis | Scorecard against the answer key; difference-in-differences with robust standard errors | `analysis/` |
| BI | Star-schema CSV export, DAX measures and a row-level-security rule for Power BI | `outputs/powerbi/`, `powerbi/MEASURES.md` |
| Orchestration | Dagster assets and a daily schedule | `orchestration/` |
| Checks | Source, model, custom generic, singular and unit tests; Python tests; CI | `dbt/tests/`, `tests/`, `.github/workflows/ci.yml` |

## Decisions worth knowing about

- **Detection never reads the answer key.** A test fails if any mart SQL mentions it; the scorecard is the only
  place the two meet.
- **Rental cover is recomputed from policy** (valuer's gross rent, stress rate, tax-band minimum) instead of trusting
  the figure on the offer. That is what exposes the network declaring rent net of a fee, found at network level
  because a per-row threshold would flag ordinary noise.
- **Cohort metrics are labelled as cohort metrics.** Offer, completion and withdrawal rates are by submission month;
  recent months are incomplete, and the user guide says so.
- **Warehouse-specific SQL is isolated** in `dbt/macros/dialect.sql` (JSON extraction, date differences, regex,
  median, rounding), so models are identical across DuckDB, PostgreSQL and Snowflake.
- **Duplicates are matched on the DIP and the broker within three days**, not on a whole-row comparison, because
  resubmissions arrive with new ids and slightly different timestamps.

## What was run, and what was not

| Item | Status |
|---|---|
| Full pipeline on DuckDB, full and quarter size | Run: 177 pass, 4 warn, 0 error; scorecard 2,467 of 2,467 |
| `dbt build` on PostgreSQL 16, full and quarter size | Run: same counts, matching issue counts, lending totals and arrears counts |
| Python tests | Run: 12 of 12 pass |
| Dagster asset graph | Loaded and materialised locally |
| GitHub Actions workflow | Written from the commands above; not yet run on GitHub |
| Snowflake | Written, **not run** (`docs/SNOWFLAKE.md`) |
| Lightdash | Metadata written, **not run** (`docs/LIGHTDASH.md`) |
| Power BI | CSV export and DAX written; the DAX has **not** been opened in Power BI Desktop |

## Limits

Simulated data; a rebuild-in-full pipeline rather than incremental loads; a single stress-rate rule and gross-rent
basis; the status history is derived from timestamps. `docs/QA.md` lists these and what each check does and does not
prove.

## Layout

```text
simulate/       seeded generator and planted defects        analysis/       scorecard, impact estimate, BI export
dbt/            project, profiles, macros, tests, seeds     orchestration/  Dagster definitions
docs/           QA, assumptions, metrics, user guide,       powerbi/        DAX measures and row-level security
                impact note, Snowflake and Lightdash        scripts/        warehouse loader
tests/          Python tests                                run.py          one command for the whole pipeline
```
