# Lightdash: the BI layer from the same dbt YAML

Status: **written, not run.** The Lightdash metadata is in the dbt YAML and the PostgreSQL target is tested, but
Lightdash itself was not started when this was built (the build environment had no running Docker). The steps below
are the intended path.

Lightdash reads metrics, dimensions and joins from the dbt project's YAML, so the definitions in `docs/METRICS.md`
live in one place. It does not support DuckDB, which is why the project also builds on PostgreSQL.

## What is already defined in the YAML

- **Metrics** under each column's `meta.metrics`: applications, offers issued, completed and withdrawn
  applications, mean and median days to offer, completions, gross lending, average loan.
- **Joins** under `fct_applications` `meta.lightdash.joins`: broker and product dimensions.
- **Owners** under each model's `meta.owner`, which show in the docs and in the metrics glossary.

The dbt semantic layer (MetricFlow) also has two semantic models and eight metrics in
`dbt/models/marts/semantic_models.yml`; Lightdash's own metrics and MetricFlow's are two translations of the same
glossary, and the glossary wins if they disagree.

## Steps

1. Start PostgreSQL and load the data: `python run.py --scale 1 --target postgres` with `PGHOST`, `PGUSER`,
   `PGPASSWORD`, `PGDATABASE` set (see `dbt/profiles.yml`).
2. Run Lightdash, either Lightdash Cloud's free tier or the self-hosted Docker Compose from Lightdash's own
   instructions, and connect it to the PostgreSQL database and this dbt project.
3. `lightdash deploy` compiles the project and publishes the explores.
4. Build the charts: gross lending by completion month and funding partner; funnel rates by submission month;
   days to offer by month; line utilisation by partner; issue counts by type.

## Row-level access for funding partners (not yet applied)

Lightdash restricts rows by user attribute with an `sql_filter` on the model's meta. For the partner report, add to
`fct_funding_monthly`, `fct_loan_book_monthly` and `fct_completions`:

```yaml
meta:
  sql_filter: "${lightdash.attribute.partner_id} = partner_id OR ${lightdash.attribute.is_internal} = 'true'"
```

and give each partner's users a `partner_id` attribute (and internal users `is_internal = true`). This mirrors the
Power BI rule in `powerbi/MEASURES.md`. Check the attribute syntax against the Lightdash version you deploy; it has
changed between releases, and it is not applied in this repository so that the models build unchanged without it.
