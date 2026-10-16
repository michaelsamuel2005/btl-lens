# Power BI measures and model

Load the CSV files in `outputs/powerbi/` (or connect to the `marts` schema on Snowflake or PostgreSQL). The model
is a star schema: `dim_date`, `dim_broker`, `dim_product`, `dim_rate_card`, `dim_funding_partner` relate one-to-many
to the fact tables, single direction. Relate `dim_date[date_day]` to `fct_completions[completion_date]` (active),
`fct_applications[submitted_date]` and `fct_loan_book_monthly[snapshot_month]`.

Every measure below is the Power BI form of a definition in `docs/METRICS.md`; the two must agree.

```dax
Gross Lending = SUM ( fct_completions[loan_amount] )
Completions = COUNTROWS ( fct_completions )
Average Loan = DIVIDE ( [Gross Lending], [Completions] )

Applications = COUNTROWS ( fct_applications )
Offers Issued = CALCULATE ( [Applications], fct_applications[reached_offer] = TRUE () )
Completed Applications = CALCULATE ( [Applications], fct_applications[is_completed] = TRUE () )
Withdrawn Applications = CALCULATE ( [Applications], fct_applications[is_withdrawn] = TRUE () )
Offer Rate % = DIVIDE ( [Offers Issued], [Applications] )
Completion Rate % = DIVIDE ( [Completed Applications], [Applications] )
Withdrawal Rate % = DIVIDE ( [Withdrawn Applications], [Applications] )

-- Timing measures average only cases that reached the stage; the mart leaves others null.
Mean Days to Offer = AVERAGE ( fct_applications[days_to_offer] )
Median Days to Offer = MEDIAN ( fct_applications[days_to_offer] )
Mean Valuation Days = AVERAGE ( fct_applications[valuation_days] )

AVM Share % =
    DIVIDE (
        CALCULATE ( [Applications], fct_applications[avm_used] = TRUE () ),
        CALCULATE ( [Applications], fct_applications[purpose] = "remortgage", fct_applications[feature_eligible] = TRUE () )
    )

Allocated Lending = SUM ( fct_funding_monthly[allocated_gbp] )
Funding Line = SUM ( fct_funding_monthly[monthly_capacity_gbp] )
Utilisation % = DIVIDE ( [Allocated Lending], [Funding Line] )
Months Over Line = CALCULATE ( COUNTROWS ( fct_funding_monthly ), fct_funding_monthly[is_over_line] = TRUE () )

-- Loan book measures are taken at a selected month; with no month selected they use the latest snapshot.
Latest Snapshot = CALCULATE ( MAX ( fct_loan_book_monthly[snapshot_month] ), ALLSELECTED ( dim_date ) )
Live Loans = CALCULATE ( COUNTROWS ( fct_loan_book_monthly ), fct_loan_book_monthly[loan_status] = "live" )
Book Balance = CALCULATE ( SUM ( fct_loan_book_monthly[balance] ), fct_loan_book_monthly[loan_status] = "live" )
Weighted Average LTV % =
    DIVIDE (
        SUMX ( FILTER ( fct_loan_book_monthly, [loan_status] = "live" ), [balance] * [ltv_current_pct] / 100 ),
        [Book Balance]
    )
Arrears 3+ Months % =
    DIVIDE (
        CALCULATE ( [Live Loans], fct_loan_book_monthly[is_in_arrears_3_plus] = TRUE () ),
        [Live Loans]
    )

Maturities = COUNTROWS ( fct_product_transfers )
Retention Rate % = DIVIDE ( CALCULATE ( [Maturities], fct_product_transfers[is_retained] = TRUE () ), [Maturities] )

Mispriced Offers = CALCULATE ( COUNTROWS ( fct_offers ), fct_offers[priced_on_expected_card] = FALSE () )
Data Quality Issues = SUM ( dq_summary[issues] )
```

## Row-level security for funding partners

Each funding partner may see only its own loans and allocations. Create a role per partner with the filter
`[partner_id] = "FP01"` on `dim_funding_partner`, or one dynamic role using a user-to-partner mapping table:

```dax
-- on dim_funding_partner, dynamic role "Funding partner"
[partner_id] = LOOKUPVALUE ( partner_users[partner_id], partner_users[user_principal_name], USERPRINCIPALNAME () )
```

`fct_funding_monthly`, `fct_loan_book_monthly` and `fct_completions` all filter through `dim_funding_partner`, so the
one rule covers the partner report. The same rule is written for Lightdash in `docs/LIGHTDASH.md`.
