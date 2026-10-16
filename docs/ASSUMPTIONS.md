# Assumptions and what is simulated

btl-lens runs on data it generates itself. Nothing in it is Landbay's, or any other lender's, data, pricing or
policy. The shape of the business (brokers, networks, decisions in principle, valuations, offers, completions,
funding lines, product transfers) follows how UK buy-to-let marketplace lending works in general; every number is
a parameter in `simulate/config.py` and is illustrative.

## The simulated business

- Period 1 January 2023 to 30 September 2026, about 1,000 decisions in principle a month growing 0.6% a month with
  seasonality; 400 brokers in 25 networks (one of them is directly authorised firms); 16 products in two ranges (Core for standard property, Specialist for
  small HMOs and small multi-unit blocks).
- Three purposes: purchase, remortgage and product transfer; two borrower types (individual and limited company);
  ten regions with their own typical values and yields.
- Four funding partners with monthly lines and scopes (all cases; Core only; standard property up to 75% LTV). One
  partner's line ends in December 2024 and another starts in April 2024.
- A bank rate path with the shape of 2023 to 2026, and a house-price index applied to the loan book. Neither is a
  record of actual rates or prices.
- Underwriting policy: minimum rental cover 125% (limited companies and basic-rate taxpayers) or 145% (higher-rate
  taxpayers); stress rate is the pay rate for fixes of five years or more, otherwise the higher of pay rate plus 2
  points and 5.5%.

## The feature being evaluated

An "instant AVM remortgage" option launches on 6 April 2026. Eligible cases (remortgage, standard property or small
HMO, up to 75% LTV, up to 15 mortgaged properties) can take an automated valuation instead of a physical one: about
a day instead of one to two weeks. In the simulation 70% of eligible post-launch cases choose it, and it also lowers
the chance of withdrawal by 5 points for those who take it.

Two things are built in to make the evaluation honest rather than easy: a background speed-up in underwriting from
January 2026 that affects every case (so a before-and-after comparison on eligible cases is biased), and a
60-day censoring window at the end of the data (so the newest cases are not judged before they can resolve).

## The planted defects

Ten defect types, listed in `simulate/config.py` and written to `data/ground_truth/defects.csv`. They are kept
independent of each other so each one can be scored on its own (an orphaned broker id is never placed on a
resubmission pair or on the network that declares net rent). The answer key also lists any funding-partner
over-capacity that arises from the simulation itself, not only the planted months.

## Choices that matter

- **Defect detection never reads the answer key.** A test fails if the marts' SQL mentions it.
- **Rental cover is recomputed from policy** for every offer rather than read from the offer document, using the
  valuer's gross rent.
- **Cohort metrics** (offer rate, completion rate, withdrawal rate) use the submission month as the denominator, so
  recent months are incomplete until cases resolve; the dashboard guide says so.
- **One definition per metric**, in `docs/METRICS.md`, with an owner; BI measures translate it.
- **Dialect differences** are isolated in `dbt/macros/dialect.sql`, so the models themselves contain no
  warehouse-specific SQL.

## What a real implementation would change

Real source systems have more statuses and reversals than a timestamped history captures; real policy has more
branches; real data arrives incrementally (this project rebuilds in full, which is fine at this size and is not how
a production pipeline would run); and real defects are discovered, not planted. The rules here are a model of how
to find and handle problems, not a catalogue of them.
