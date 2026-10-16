#!/usr/bin/env python3
"""Load the simulated source extracts (data/raw) into a warehouse, so dbt can run there instead of on DuckDB.

    python scripts/load_warehouse.py --target postgres    # PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
    python scripts/load_warehouse.py --target snowflake   # SNOWFLAKE_ACCOUNT, _USER, _PASSWORD, _ROLE, _WAREHOUSE, _DATABASE

Tables land in a schema called `raw`, one per source file, with numeric columns typed and everything else as text; the dbt
staging models do the rest of the typing, exactly as they do for the CSV files on DuckDB. `portal_events.payload` is loaded as JSON
(jsonb on PostgreSQL, VARIANT on Snowflake), because the staging model reads it with the `json_get` macro.
Loading is idempotent: each table is dropped and recreated.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

import pandas as pd

RAW = Path(os.environ.get("BTL_LENS_RAW_DIR", Path(__file__).resolve().parents[1] / "data" / "raw"))
CSV_TABLES = ["brokers", "products", "rate_cards", "funding_partners", "dips", "applications", "application_status_history",
              "valuations", "offers", "completions", "funding_allocations", "loan_book_monthly", "product_transfers"]


def read_csv(name: str) -> pd.DataFrame:
    """Numbers load as numbers (the source tests check ranges on them); dates and timestamps stay text for staging to cast."""
    return pd.read_csv(RAW / f"{name}.csv", keep_default_na=False, na_values=[""])


def pg_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "bigint"
    if pd.api.types.is_float_dtype(series):
        return "double precision"
    return "text"


def read_events() -> pd.DataFrame:
    rows = [json.loads(line) for line in (RAW / "portal_events.jsonl").read_text().splitlines() if line]
    df = pd.DataFrame(rows)
    df["payload"] = df["payload"].map(json.dumps)
    return df


def load_postgres() -> None:
    import psycopg2
    con = psycopg2.connect(host=os.environ.get("PGHOST", "localhost"), port=os.environ.get("PGPORT", "5432"),
                           user=os.environ.get("PGUSER", "btl"), password=os.environ.get("PGPASSWORD", "btl"),
                           dbname=os.environ.get("PGDATABASE", "btl_lens"))
    cur = con.cursor()
    cur.execute("create schema if not exists raw")
    for name in CSV_TABLES + ["portal_events"]:
        df = read_events() if name == "portal_events" else read_csv(name)
        cols = ", ".join(f'"{c}" ' + ("jsonb" if (name == "portal_events" and c == "payload") else pg_type(df[c])) for c in df.columns)
        cur.execute(f'drop table if exists raw."{name}" cascade')
        cur.execute(f'create table raw."{name}" ({cols})')
        buf = io.StringIO()
        df.to_csv(buf, index=False, header=False)
        buf.seek(0)
        cur.copy_expert(f'copy raw."{name}" from stdin with (format csv, null \'\')', buf)
        print(f"  raw.{name}: {len(df):,} rows")
    con.commit()
    con.close()


def load_snowflake() -> None:
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas
    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"], password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"), warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"))
    db = os.environ.get("SNOWFLAKE_DATABASE", "BTL_LENS")
    cur = con.cursor()
    cur.execute(f"create database if not exists {db}")
    cur.execute(f"use database {db}")
    cur.execute("create schema if not exists raw")
    cur.execute("use schema raw")
    for name in CSV_TABLES + ["portal_events"]:
        df = read_events() if name == "portal_events" else read_csv(name)
        target = f"{name}_text" if name == "portal_events" else name
        cur.execute(f"drop table if exists {target}")
        write_pandas(con, df, target.upper(), database=db.upper(), schema="RAW", auto_create_table=True, overwrite=True,
                     quote_identifiers=False)
        if name == "portal_events":                       # keep the payload as VARIANT, as the staging model expects
            others = ", ".join(c for c in df.columns if c != "payload")
            cur.execute(f"create or replace table portal_events as select {others}, parse_json(payload) as payload from {target}")
            cur.execute(f"drop table {target}")
        print(f"  raw.{name}: {len(df):,} rows")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["postgres", "snowflake"], required=True)
    args = ap.parse_args()
    print(f"Loading {RAW} into {args.target}")
    {"postgres": load_postgres, "snowflake": load_snowflake}[args.target]()
