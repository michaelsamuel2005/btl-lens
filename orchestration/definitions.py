"""Dagster definitions: the source extracts, every dbt model as an asset, and the analyses that follow the build.

    dagster dev -m orchestration.definitions          # local UI with the asset graph and lineage
    dagster asset list -m orchestration.definitions
    dagster job launch -m orchestration.definitions -j daily_refresh

The dbt models appear in Dagster with their dbt lineage (dagster-dbt reads the manifest); the daily schedule runs
the simulation refresh, `dbt build`, the scorecard, the feature-impact note and the BI export in order.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dagster import (AssetExecutionContext, AssetKey, AssetSpec, Definitions, MaterializeResult, ScheduleDefinition, asset,
                     define_asset_job, multi_asset)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "dbt"
# dbt runs with the dbt folder as its working directory under Dagster, so paths are made absolute here.
os.environ.setdefault("BTL_LENS_DB", str(ROOT / "outputs" / "btl_lens.duckdb"))
os.environ.setdefault("BTL_LENS_RAW_DIR", str(ROOT / "data" / "raw"))
dbt_project = DbtProject(project_dir=DBT_DIR, profiles_dir=DBT_DIR)
dbt_project.prepare_if_dev()

# The dbt sources are keyed ["raw", <table>] by dagster-dbt's default translator; the simulation step produces all of them.
RAW_TABLES = ["brokers", "products", "rate_cards", "funding_partners", "dips", "applications", "application_status_history",
              "valuations", "offers", "completions", "funding_allocations", "loan_book_monthly", "product_transfers", "portal_events"]


def run(cmd):
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stdout[-2000:] + out.stderr[-2000:])
    return out.stdout


@multi_asset(
    specs=[AssetSpec(AssetKey(["raw", t]), group_name="sources",
                     description=f"Source-system extract data/raw/{t} written by the seeded simulator") for t in RAW_TABLES],
)
def raw_extracts(context: AssetExecutionContext):
    out = run([sys.executable, "-m", "simulate"])
    context.log.info(out)
    for t in RAW_TABLES:
        yield MaterializeResult(asset_key=AssetKey(["raw", t]))


@dbt_assets(manifest=dbt_project.manifest_path)
def btl_lens_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


@asset(deps=[btl_lens_dbt_assets], group_name="analysis", description="Detected issues against the planted answer key (outputs/scorecard.json).")
def scorecard(context: AssetExecutionContext) -> MaterializeResult:
    out = run([sys.executable, "-m", "analysis.scorecard"])
    s = json.loads((ROOT / "outputs" / "scorecard.json").read_text())
    return MaterializeResult(metadata={"recall": s["recall"], "planted": s["planted"], "caught": s["caught"], "false_alarms": s["false_alarms"]})


@asset(deps=[btl_lens_dbt_assets], group_name="analysis", description="Difference-in-differences evaluation of the instant AVM launch (docs/FEATURE_IMPACT.md).")
def feature_impact(context: AssetExecutionContext) -> MaterializeResult:
    run([sys.executable, "-m", "analysis.feature_impact"])
    r = json.loads((ROOT / "outputs" / "feature_impact.json").read_text())
    return MaterializeResult(metadata={"days_to_offer_did": r["days_to_offer"]["estimate"], "withdrawal_did": r["withdrawal_rate"]["estimate"]})


@asset(deps=[btl_lens_dbt_assets], group_name="analysis", description="Star-schema CSV export for Power BI (outputs/powerbi).")
def powerbi_export(context: AssetExecutionContext) -> MaterializeResult:
    out = run([sys.executable, "-m", "analysis.export_powerbi"])
    return MaterializeResult(metadata={"stdout": out[-1500:]})


daily_refresh = define_asset_job("daily_refresh", selection="*")
daily_schedule = ScheduleDefinition(job=daily_refresh, cron_schedule="0 6 * * *", execution_timezone="Europe/London")

defs = Definitions(
    assets=[raw_extracts, btl_lens_dbt_assets, scorecard, feature_impact, powerbi_export],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
    jobs=[daily_refresh],
    schedules=[daily_schedule],
)
