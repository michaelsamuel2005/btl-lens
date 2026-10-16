# Using the dashboards: a guide for the people who read them

This is for finance, operations, credit risk, treasury and product colleagues who use the reports built on these
tables, not for the people who maintain the pipeline. Status: the tables, the Power BI export and DAX measures
(`powerbi/MEASURES.md`) and the Lightdash metadata are built and tested; the report layouts below are the
intended design, because no Power BI Desktop file or Lightdash instance was produced when this was built. Definitions of every measure are in `docs/METRICS.md`, one
owner per metric; if a number looks wrong, ask that owner first.

## Which report answers which question

| If you want to know | Look at | Owner |
|---|---|---|
| How much we lent last month, and to whom | Lending and pipeline: **Gross lending** by completion month, split by product, broker network, funding partner | Finance |
| Whether cases are getting through the funnel | Lending and pipeline: **Offer rate**, **Completion rate**, **Withdrawal rate**, **Days to offer**, by submission month | Operations analytics |
| Whether a funding line is close to its limit | Funding partner report: **Line utilisation**; over 100% is a breach | Treasury |
| How the loan book is performing | Funding partner report: **Current LTV**, **Arrears 3+ months**, by snapshot month | Credit risk |
| Whether the instant AVM launch worked | `docs/FEATURE_IMPACT.md` and the **AVM share** tile | Product analytics |
| Whether the data can be trusted today | Data quality register: issues by type | Data team |

## Reading the numbers: four things that trip people up

**Recent months are incomplete.** Offer, completion and withdrawal rates are by the month a case was *submitted*. A
case submitted last week has not finished, so last month's completion rate will rise as its cases resolve. Compare
months that are old enough (about three months), or use gross lending, which is by the month funds were released.

**"Completed" means funds released.** The source system's own completion date is sometimes the offer-accepted date.
The reports use the date funds were released. The register lists the 1,017 records where the two differ.

**Days to offer only counts cases that reached an offer.** A case that was withdrawn or declined has no days to
offer. A fall in the average can mean faster offers or a change in which cases get one; look at the offer rate next
to it.

**Rental cover is recomputed.** It uses the valuer's gross rent and the stress rate in policy, not the figure printed
on the offer. One broker network declares rent net of a fee, so its declared figures read about 10% low; the
register explains this, and policy rental cover is unaffected because it uses the valuer's figure.

## Filtering and drilling

Each report is designed to filter by month, region, product range, broker network and purpose. Broker network is the grouping to
use for distribution questions; individual broker ids are for investigating, not for league tables, because many
brokers have very few cases.

## When something looks wrong

1. Check the register (`dq_issues`) for the record or its type: many apparent problems are already listed there,
   with what the reports do about them.
2. Check the metric's definition and owner in `docs/METRICS.md`.
3. If neither explains it, tell the data team the report, the filters you applied and the number you expected.

## What is not in the reports

Free-text notes are never carried into the reports, because they can contain personal data. Funding partners are meant to see
only their own allocations and loans (row-level security, specified but not applied; see `powerbi/MEASURES.md` and `docs/LIGHTDASH.md`).
