# Running on Snowflake

Status: **written, not run.** The project has been built and tested on DuckDB and PostgreSQL (see `docs/QA.md`).
The Snowflake profile, adapter macros and loader exist, but no Snowflake account was available when this was built,
so none of it has been executed against Snowflake. Treat the steps below as the intended path, and expect to fix
small things on the first run.

## Steps

1. Create a Snowflake trial account and note the account identifier, a user, and the default `COMPUTE_WH` warehouse.
2. Install the extras: `pip install -r requirements-snowflake.txt`.
3. Set the environment variables used by `dbt/profiles.yml` and the loader:

   ```bash
   export SNOWFLAKE_ACCOUNT=<org>-<account>
   export SNOWFLAKE_USER=<user>
   export SNOWFLAKE_PASSWORD=<password>        # do not commit this; use a secrets manager outside a trial
   export SNOWFLAKE_ROLE=ACCOUNTADMIN          # a trial is fine; use a narrower role for anything real
   export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   export SNOWFLAKE_DATABASE=BTL_LENS
   ```

4. Run `python run.py --target snowflake`. It simulates the data, loads it into `BTL_LENS.RAW`
   (`scripts/load_warehouse.py`), and runs `dbt build --target snowflake`.

## What differs from DuckDB

All warehouse-specific SQL lives in `dbt/macros/dialect.sql`, dispatched on the adapter:

| Macro | Purpose | Snowflake form |
|---|---|---|
| `json_get` | Read a field from the portal-event payload | `(payload:path)::string` on a `VARIANT` column |
| `days_between` | Decimal days between two timestamps | `datediff('second', ...) / 86400.0` |
| `regex_matches` | The pattern used to find names in free-text notes | `regexp_like(...)` |
| `median_of`, `round_to`, `type_double` | Median and rounding that every target accepts | the default forms |

The loader writes `portal_events.payload` as `VARIANT` with `parse_json`, and the other columns with the types
pandas infers; the staging models cast the rest.

## Things to check on a first run

- `loaded_at_field` source-freshness settings are set for the sources; run `dbt source freshness` once.
- Snapshot tables (`snapshots` schema) are created on first build; a rerun with a changed column type needs the
  schema dropped, as it did on PostgreSQL during testing.
- Unit-test expectations compare formatted numbers; the models cast their outputs to fixed types to make that
  stable across warehouses, and Snowflake may show a case that PostgreSQL did not.
- Cost: an X-Small warehouse with auto-suspend at 60 seconds is enough; the whole build is minutes of compute.

If you run it, record the result honestly in the README (what passed, what you had to change) rather than assuming
it matches the other two targets.
