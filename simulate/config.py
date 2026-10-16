"""Parameters of the simulated buy-to-let mortgage marketplace. Everything here is illustrative.

The scheme is a marketplace lender: brokers submit cases through a portal, the lender underwrites them, and
completed loans are allocated to funding partners (banks and institutions) that hold them on their balance
sheets. Nothing here is a real lender's data, pricing or policy.
"""
from __future__ import annotations

from datetime import date

SEED = 2026
START = date(2023, 1, 1)
END = date(2026, 9, 30)            # last day of the simulated period
DIPS_PER_MONTH = 1000              # decisions in principle a month, before trend and seasonality
MONTHLY_GROWTH = 0.006             # volume trend, a month
SEASONALITY = {1: 0.95, 2: 1.00, 3: 1.08, 4: 1.02, 5: 1.05, 6: 1.06, 7: 1.02, 8: 0.90, 9: 1.05, 10: 1.06, 11: 1.00, 12: 0.80}

# Feature launch: an "instant AVM remortgage" option in the broker portal. Eligible cases can take an
# automated valuation instead of a physical one, which removes the valuation wait. Ineligible cases are the
# comparison group for the post-launch evaluation (docs/FEATURE_IMPACT.md).
FEATURE_LAUNCH = date(2026, 4, 6)
FEATURE_ELIGIBLE_PROPERTY_TYPES = ("standard", "hmo_small")
FEATURE_MAX_LTV = 75.0
FEATURE_MAX_PORTFOLIO = 15
FEATURE_AVM_TAKE_UP = 0.70         # share of eligible post-launch remortgage cases that choose the AVM
PHYSICAL_VALUATION_DAYS = (7.0, 16.0)   # uniform range, instruction to report
AVM_VALUATION_DAYS = (0.2, 2.0)
FEATURE_TRUE_EFFECTS = {           # what the simulation builds in, for the answer key
    "avm_valuation_days_saved": (sum(PHYSICAL_VALUATION_DAYS) - sum(AVM_VALUATION_DAYS)) / 2,   # difference of means
    "avm_withdrawal_rate_reduction": 0.05,
}
# A background improvement in underwriting speed from January 2026 that affects every case. A naive
# before-and-after comparison would attribute it to the feature; the comparison group removes it.
BACKGROUND_SPEEDUP_FROM = date(2026, 1, 1)
BACKGROUND_SPEEDUP_DAYS = 1.5

# Policy (illustrative, in the spirit of UK buy-to-let underwriting)
MIN_RENTAL_COVER = {"basic": 125.0, "higher": 145.0, "limited_company": 125.0}   # percent
STRESS_FLOOR_PCT = 5.5             # stress rate for products fixed for under five years: max(pay rate + 2, floor)
STRESS_UPLIFT_PCT = 2.0
PORTFOLIO_LANDLORD_FROM = 4        # four or more mortgaged buy-to-let properties

REGIONS = {  # region: (share of cases, typical property value, gross rental yield)
    "London": (0.22, 520_000, 0.048),
    "South East": (0.17, 390_000, 0.052),
    "East of England": (0.09, 330_000, 0.055),
    "South West": (0.08, 310_000, 0.054),
    "West Midlands": (0.09, 230_000, 0.064),
    "East Midlands": (0.07, 215_000, 0.066),
    "North West": (0.11, 200_000, 0.070),
    "Yorkshire and the Humber": (0.08, 190_000, 0.070),
    "North East": (0.04, 150_000, 0.078),
    "Wales": (0.05, 185_000, 0.066),
}
PROPERTY_TYPES = {"standard": 0.78, "hmo_small": 0.15, "mufb_small": 0.07}
PURPOSES = {"purchase": 0.42, "remortgage": 0.46, "product_transfer": 0.12}
BORROWER_TYPES = {"individual": 0.45, "limited_company": 0.55}
TAX_BANDS_INDIVIDUAL = {"basic": 0.45, "higher": 0.55}

# Funding partners: fictional names. Each has a line (start, end) and a monthly capacity in pounds.
FUNDING_PARTNERS = [
    {"partner_id": "FP01", "partner_name": "Northgate Bank", "line_start": date(2023, 1, 1), "line_end": None,
     "monthly_capacity_gbp": 45_000_000, "scope": "all"},
    {"partner_id": "FP02", "partner_name": "Avon Capital Partners", "line_start": date(2023, 1, 1), "line_end": None,
     "monthly_capacity_gbp": 30_000_000, "scope": "core_only"},
    {"partner_id": "FP03", "partner_name": "Meridian Building Society", "line_start": date(2024, 4, 1), "line_end": None,
     "monthly_capacity_gbp": 25_000_000, "scope": "standard_75"},
    {"partner_id": "FP04", "partner_name": "Harbour Credit", "line_start": date(2023, 1, 1), "line_end": date(2024, 12, 31),
     "monthly_capacity_gbp": 20_000_000, "scope": "all"},
]

# Products. range: Core (standard property) or Specialist (small HMO, small multi-unit block).
PRODUCTS = [
    # product_id, range, property scope, borrower scope, term type, fixed years, max ltv, fee pct, purposes
    ("CORE-2F-65-3", "Core", "standard", "both", "fixed", 2, 65, 3.0, "purchase,remortgage"),
    ("CORE-2F-75-2", "Core", "standard", "both", "fixed", 2, 75, 2.0, "purchase,remortgage"),
    ("CORE-2F-75-5", "Core", "standard", "both", "fixed", 2, 75, 5.0, "purchase,remortgage"),
    ("CORE-5F-65-3", "Core", "standard", "both", "fixed", 5, 65, 3.0, "purchase,remortgage"),
    ("CORE-5F-75-3", "Core", "standard", "both", "fixed", 5, 75, 3.0, "purchase,remortgage"),
    ("CORE-5F-80-5", "Core", "standard", "both", "fixed", 5, 80, 5.0, "purchase,remortgage"),
    ("CORE-2T-75-3", "Core", "standard", "both", "tracker", 2, 75, 3.0, "purchase,remortgage"),
    ("CORE-PT-2F-75-3", "Core", "standard", "both", "fixed", 2, 75, 3.0, "product_transfer"),
    ("CORE-PT-5F-75-3", "Core", "standard", "both", "fixed", 5, 75, 3.0, "product_transfer"),
    ("CORE-PT-2T-75-3", "Core", "standard", "both", "tracker", 2, 75, 3.0, "product_transfer"),
    ("SPEC-HMO-2F-75-3", "Specialist", "hmo_small", "both", "fixed", 2, 75, 3.0, "purchase,remortgage"),
    ("SPEC-HMO-5F-75-5", "Specialist", "hmo_small", "both", "fixed", 5, 75, 5.0, "purchase,remortgage"),
    ("SPEC-HMO-5F-75-1", "Specialist", "hmo_small", "both", "fixed", 5, 75, 1.0, "purchase,remortgage"),
    ("SPEC-MUFB-5F-75-3", "Specialist", "mufb_small", "both", "fixed", 5, 75, 3.0, "purchase,remortgage"),
    ("SPEC-PT-5F-75-3", "Specialist", "hmo_small,mufb_small", "both", "fixed", 5, 75, 3.0, "product_transfer"),
    ("SPEC-PT-2T-75-3", "Specialist", "hmo_small,mufb_small", "both", "tracker", 2, 75, 3.0, "product_transfer"),
]

# Bank base rate path (illustrative, roughly the shape of 2023-2026; not a record of actual decisions).
BANK_RATE_PATH = [
    (date(2023, 1, 1), 3.50), (date(2023, 2, 2), 4.00), (date(2023, 3, 23), 4.25), (date(2023, 5, 11), 4.50),
    (date(2023, 6, 22), 5.00), (date(2023, 8, 3), 5.25), (date(2024, 8, 1), 5.00), (date(2024, 11, 7), 4.75),
    (date(2025, 2, 6), 4.50), (date(2025, 5, 8), 4.25), (date(2025, 8, 7), 4.00), (date(2025, 11, 6), 3.75),
    (date(2026, 2, 5), 3.50), (date(2026, 5, 7), 3.50), (date(2026, 8, 6), 3.25),
]

# Planted defects (answer key in data/ground_truth/defects.csv). Rates are shares of the affected population.
DEFECTS = {
    "duplicate_application": 0.015,     # broker resubmits the same case under a new application id
    "status_out_of_order": 0.006,       # two status timestamps swapped in the history export
    "completion_date_mismatch": 0.10,   # applications.completed_at carries the offer-accepted date, not funds released
    "rent_basis_net": "network:Pennine Mortgage Network",   # one network declares rent net of a 10% management fee
    "stale_rate_card": (date(2025, 9, 8), date(2025, 9, 21), "Core"),   # Core offers priced on the superseded card for two weeks
    "avm_ineligible": 30,               # AVM used on properties outside the AVM policy
    "partner_over_capacity": [(2025, 3), (2026, 6)],   # months in which FP02 is allocated above its line
    "pii_in_notes": 50,                 # a borrower's full name typed into the free-text notes
    "orphan_broker": 20,                # applications whose broker_id is not in the broker file
    "nonpositive_loan": 10,             # loan amount of zero or negative
}
