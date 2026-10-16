"""End-to-end: a quarter-size simulation through dbt build, the scorecard and the feature evaluation, in a
temporary DuckDB file. Also checks that the pipeline never reads the answer key."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    work = tmp_path_factory.mktemp("btl")
    env = dict(os.environ, BTL_LENS_RAW_DIR=str(work / "raw"), BTL_LENS_DB=str(work / "btl_lens.duckdb"))
    subprocess.run([sys.executable, "-m", "simulate", "--scale", "0.25", "--out", str(work)], cwd=ROOT, check=True)
    r = subprocess.run(["dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:]
    return work, env, r.stdout


def test_dbt_build_passes_with_only_expected_warnings(built):
    _, _, out = built
    results = json.loads((ROOT / "dbt" / "target" / "run_results.json").read_text())["results"]
    statuses = {r["unique_id"]: r["status"] for r in results}
    assert not [k for k, v in statuses.items() if v in ("error", "fail")]
    warned = sorted(k.split(".")[2] for k, v in statuses.items() if v == "warn")      # unique_id = type.project.name.hash
    # the only warnings are the source-level monitors on planted defects and the rental-cover monitor on offers
    for w in warned:
        assert any(s in w for s in ("loan_amount", "broker_id", "rental_cover")), w


def test_scorecard_catches_every_planted_defect_with_no_false_alarms(built):
    work, env, _ = built
    from analysis.scorecard import score
    s = score(db=work / "btl_lens.duckdb", key=work / "ground_truth" / "defects.csv")
    assert s["planted"] > 500
    assert s["caught"] == s["planted"]
    assert s["false_alarms"] == 0
    assert s["defect_types_fully_caught"] == s["defect_types"] == 10


def test_unit_tests_and_snapshots_ran(built):
    results = json.loads((ROOT / "dbt" / "target" / "run_results.json").read_text())["results"]
    kinds = {r["unique_id"].split(".")[0] for r in results}
    assert {"unit_test", "snapshot", "seed", "model", "test"} <= kinds


def test_marts_never_read_the_answer_key():
    text = "\n".join(p.read_text() for p in (ROOT / "dbt").rglob("*.sql") if "dbt_packages" not in p.parts and "target" not in p.parts)
    text += "\n".join(p.read_text() for p in (ROOT / "dbt" / "models").rglob("*.yml"))
    assert "ground_truth" not in text and "defects.csv" not in text and "feature_effect" not in text


def test_feature_impact_estimate_covers_the_designed_effect(built):
    work, env, _ = built
    import duckdb
    from analysis import feature_impact as fi
    con = duckdb.connect(str(work / "btl_lens.duckdb"), read_only=True)
    df = con.sql("select * from marts.fct_feature_impact").df()
    df["eligible"] = df.feature_eligible.astype(int)
    df["post"] = df.is_post_launch.astype(int)
    d = fi.did(df, "days_to_offer", df.reached_offer)
    truth = json.loads((work / "ground_truth" / "feature_effect.json").read_text())["expected_effect_on_eligible_group"]["days_to_offer"]
    assert d["ci95"][0] - 1.0 <= truth <= d["ci95"][1] + 1.0      # within the interval, with a day's tolerance at quarter scale
    assert d["estimate"] < 0 and d["p_value"] < 0.001
