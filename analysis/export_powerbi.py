"""Export the star schema for Power BI (or any BI tool) as CSV files in outputs/powerbi/.

    python -m analysis.export_powerbi       # after `dbt build`

The marts are the model; this writes them out so Power BI Desktop can load them with the measures in
powerbi/MEASURES.md. On Snowflake or PostgreSQL the BI tool connects to the marts schema directly.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "outputs" / "btl_lens.duckdb"
OUT = ROOT / "outputs" / "powerbi"

TABLES = {
    "dim_date": "select * from marts.dim_date",
    "dim_broker": "select * from marts.dim_broker",
    "dim_product": "select * from marts.dim_product",
    "dim_rate_card": "select * from marts.dim_rate_card",
    "dim_funding_partner": "select * from marts.dim_funding_partner",
    "fct_applications": """select application_id, dip_id, broker_id, product_id, submitted_date, submitted_month, borrower_type, tax_band,
                                  property_type, purpose, region, portfolio_size, is_portfolio_landlord, property_value, loan_amount,
                                  ltv_at_application_pct, ltv_band_at_application, valuation_type, outcome, is_completed, is_withdrawn,
                                  is_declined, reached_offer, valuation_days, underwriting_days, days_to_offer, days_to_completion,
                                  rental_cover_policy_pct, rental_cover_passes, feature_eligible, is_post_launch, avm_used
                           from marts.fct_applications""",
    "fct_offers": """select offer_id, application_id, broker_id, product_id, offered_month, loan_amount, ltv_pct, initial_rate_pct,
                            rate_card_id, priced_on_expected_card, rate_difference_pct_points, rental_cover_policy_pct, rental_cover_passes,
                            is_accepted, days_to_acceptance from marts.fct_offers""",
    "fct_completions": "select * from marts.fct_completions",
    "fct_funding_monthly": "select * from marts.fct_funding_monthly",
    "fct_loan_book_monthly": "select * from marts.fct_loan_book_monthly",
    "fct_product_transfers": "select * from marts.fct_product_transfers",
    "agg_feature_impact": "select * from marts.agg_feature_impact",
    "dq_summary": "select * from quality.dq_summary",
    "dq_issues": "select issue_type, entity, record_id from quality.dq_issues",
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    for name, sql in TABLES.items():
        path = OUT / f"{name}.csv"
        con.sql(f"copy ({sql}) to '{path}' (header, delimiter ',')")
        n = con.sql(f"select count(*) from ({sql})").fetchone()[0]
        print(f"  {name:24s} {n:>9,} rows")
    print(f"written to {OUT}/")
