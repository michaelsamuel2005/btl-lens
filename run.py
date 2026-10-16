#!/usr/bin/env python3
"""Run the whole pipeline from the repository root, in order:

    python run.py                 # simulate -> dbt deps -> dbt build -> scorecard -> feature impact -> BI export
    python run.py --scale 0.25    # quarter-size data (what CI runs)
    python run.py --target snowflake   # dbt against another target (see docs/SNOWFLAKE.md); loads the raw data first

Every step prints what it did; any failure stops the run.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("BTL_LENS_DB", str(ROOT / "outputs" / "btl_lens.duckdb"))
os.environ.setdefault("BTL_LENS_RAW_DIR", str(ROOT / "data" / "raw"))

p = argparse.ArgumentParser()
p.add_argument("--scale", type=float, default=1.0)
p.add_argument("--target", default="duckdb")
p.add_argument("--skip-simulate", action="store_true")
a = p.parse_args()


def step(n, title, cmd):
    print(f"\n[{n}] {title}\n    $ {' '.join(cmd)}")
    t = time.time()
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"step {n} failed ({title})")
    print(f"    done in {time.time() - t:.0f}s")


dbt = ["dbt", "--project-dir", "dbt", "--profiles-dir", "dbt"]
(ROOT / "outputs").mkdir(exist_ok=True)
if not a.skip_simulate:
    step(1, "Simulate the marketplace and write the raw extracts", [sys.executable, "-m", "simulate", "--scale", str(a.scale)])
step(2, "Install dbt packages", ["dbt", "deps", "--project-dir", "dbt", "--profiles-dir", "dbt"])
if a.target != "duckdb":
    step(3, f"Load the raw extracts into the {a.target} warehouse", [sys.executable, "scripts/load_warehouse.py", "--target", a.target])
step(4, f"dbt build on {a.target} (models, tests, unit tests, snapshots, seeds)",
     ["dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt", "--target", a.target])
if a.target == "duckdb":
    step(5, "Score detections against the planted answer key", [sys.executable, "-m", "analysis.scorecard"])
    step(6, "Evaluate the feature launch (difference-in-differences)", [sys.executable, "-m", "analysis.feature_impact"])
    step(7, "Export the star schema for Power BI", [sys.executable, "-m", "analysis.export_powerbi"])
print("\nDone.")
