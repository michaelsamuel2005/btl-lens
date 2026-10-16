"""Score the data-quality layer against the planted answer key.

    python -m analysis.scorecard            # after `dbt build`

Compares `quality.dq_issues` (what the pipeline detected) with `data/ground_truth/defects.csv` (what the simulator
planted) by issue type and record id. The pipeline never reads the answer key; a test enforces that
(tests/test_pipeline.py). Writes outputs/scorecard.json and outputs/scorecard.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "outputs" / "btl_lens.duckdb"
KEY = ROOT / "data" / "ground_truth" / "defects.csv"


def score(db: Path = DB, key: Path = KEY) -> dict:
    con = duckdb.connect(str(db), read_only=True)
    found = con.sql("select issue_type, record_id, detail from quality.dq_issues").df()
    planted = pd.read_csv(key)
    rows = []
    for t in sorted(set(planted.defect_type) | set(found.issue_type)):
        p = set(planted.loc[planted.defect_type == t, "record_id"])
        f = set(found.loc[found.issue_type == t, "record_id"])
        rows.append({
            "issue_type": t,
            "planted": len(p),
            "detected": len(f),
            "caught": len(p & f),
            "missed": len(p - f),
            "false_alarms": len(f - p) if p else 0,          # types that were never planted are findings, not false alarms
            "not_planted_findings": len(f) if not p else 0,
        })
    df = pd.DataFrame(rows)
    planted_rows = df[df.planted > 0]
    summary = {
        "planted": int(planted_rows.planted.sum()),
        "caught": int(planted_rows.caught.sum()),
        "missed": int(planted_rows.missed.sum()),
        "false_alarms": int(planted_rows.false_alarms.sum()),
        "recall": round(float(planted_rows.caught.sum() / planted_rows.planted.sum()), 4),
        "defect_types": int((planted_rows.planted > 0).sum()),
        "defect_types_fully_caught": int(((planted_rows.caught == planted_rows.planted) & (planted_rows.false_alarms == 0)).sum()),
        "additional_findings": {r.issue_type: int(r.detected) for r in df.itertuples() if r.planted == 0},
        "by_type": rows,
    }
    return summary


def to_markdown(s: dict) -> str:
    lines = ["| Issue type | Planted | Detected | Caught | Missed | False alarms |", "|---|---:|---:|---:|---:|---:|"]
    for r in s["by_type"]:
        if r["planted"]:
            lines.append(f"| {r['issue_type']} | {r['planted']:,} | {r['detected']:,} | {r['caught']:,} | {r['missed']:,} | {r['false_alarms']:,} |")
    lines.append(f"| **Total** | **{s['planted']:,}** | | **{s['caught']:,}** | **{s['missed']:,}** | **{s['false_alarms']:,}** |")
    extra = [f"{k} ({v})" for k, v in s["additional_findings"].items()]
    if extra:
        lines.append("")
        lines.append("Findings that were not planted but follow from planted defects: " + ", ".join(extra) + ".")
    return "\n".join(lines)


if __name__ == "__main__":
    s = score()
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "scorecard.json").write_text(json.dumps(s, indent=2))
    (ROOT / "outputs" / "scorecard.md").write_text(to_markdown(s) + "\n")
    print(to_markdown(s))
    print(f"\nrecall {s['recall']:.1%}; {s['defect_types_fully_caught']} of {s['defect_types']} defect types fully caught with no false alarms")
