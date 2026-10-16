# Metrics glossary

One definition and one owner per metric. The dbt marts implement these definitions; `powerbi/MEASURES.md` and the
Lightdash metrics in the dbt YAML are translations of this page, not alternatives to it. Change a definition here
first, then the code.

| Metric | Definition | Grain and source | Owner |
|---|---|---|---|
| **Gross lending** | Sum of `loan_amount` over completed loans, by the month funds were released (`completion_month`). Not the offer date, not the offer-accepted date. | `fct_completions` | Finance |
| **Completions** | Count of completed loans (funds released). | `fct_completions` | Finance |
| **Applications** | Count of genuine applications: broker resubmissions within three days of the same DIP are one application, and records with a non-positive loan are excluded. | `fct_applications` | Operations analytics |
| **Offer rate** | Applications that received an offer / applications, by month submitted. Cohort-based: the denominator is the submission month, so recent months are incomplete until their cases resolve. | `fct_applications.reached_offer` | Operations analytics |
| **Completion rate** | Completed applications / applications, by month submitted. Same cohort caveat. | `fct_applications.is_completed` | Operations analytics |
| **Withdrawal rate** | Withdrawn applications / applications, by month submitted. | `fct_applications.is_withdrawn` | Operations analytics |
| **Days to offer** | Days (decimal) from submission to offer, from the status history; only cases that reached offer; mean and median reported. | `fct_applications.days_to_offer` | Operations analytics |
| **Valuation days** | Days from valuation instruction to report. Null where the history is out of order. | `fct_applications.valuation_days` | Operations analytics |
| **AVM share** | Eligible remortgage applications that used an automated valuation / eligible remortgage applications. | `fct_applications.avm_used` | Product analytics |
| **LTV at completion** | Loan / valuer's market value at completion. | `fct_completions.ltv_at_completion_pct` | Credit risk |
| **Current LTV** | Balance / indexed property value, at the snapshot month; weighted by balance when aggregated. | `fct_loan_book_monthly.ltv_current_pct` | Credit risk |
| **Rental cover (policy)** | Valuer's gross annual rent / (loan x stress rate). Stress rate: pay rate for fixes of five years or more; otherwise max(pay rate + 2, 5.5). Minimum 125% (limited companies, basic-rate taxpayers) or 145% (higher-rate taxpayers). Always recomputed; never read from the offer document. | `fct_offers.rental_cover_policy_pct` | Credit risk |
| **Arrears 3+ months** | Live loans three or more months in arrears / live loans, at the snapshot month. | `fct_loan_book_monthly.is_in_arrears_3_plus` | Credit risk |
| **Allocated lending** | Lending allocated to a funding partner in a month. | `fct_funding_monthly.allocated_gbp` | Treasury |
| **Line utilisation** | Allocated lending / the partner's monthly line. Over 100% is a breach and appears in the data-quality register. | `fct_funding_monthly.utilisation_pct` | Treasury |
| **Retention rate** | Maturities that transferred to a new product / maturities, by maturity month. | `fct_product_transfers.is_retained` | Retention |
| **Mispriced offers** | Offers not priced on the rate card live when the case was submitted. | `fct_offers.priced_on_expected_card` | Pricing |
| **Data-quality issues** | Records in the data-quality register, by issue type. | `dq_issues` | Data team |

Conventions: percentages are stored as 0 to 100 in `_pct` columns and as 0 to 1 in rates computed from booleans;
money is in pounds; months are the first day of the month; "days" are decimals from timestamps.
