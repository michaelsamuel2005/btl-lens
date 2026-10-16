"""Generate the simulated marketplace: raw source extracts in data/raw/ and the answer key in data/ground_truth/.

    python -m simulate                 # full size, about 20 seconds
    python -m simulate --scale 0.25    # quarter size, for tests

The extracts imitate what source systems export: a broker portal (brokers, DIPs, applications, status history,
portal events as JSON lines), underwriting (valuations, offers), completions, pricing (products, rate cards),
treasury (funding partners, allocations), servicing (monthly loan book, product transfers). Defects are planted
on purpose and logged; the dbt layer has to find them (see docs/QA.md).
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

NETWORKS = [
    "Pennine Mortgage Network", "Thames Valley Advisers", "Castle Street Partners", "Harrowgate Financial",
    "Brightwell Mortgages", "Solent Property Finance", "Kingsway Brokers", "Albion Intermediaries",
    "Severn Mortgage Club", "Orchard Advisers", "Cromwell Finance Network", "Lakeside Mortgages",
    "Cathedral Financial", "Beacon Property Finance", "Riverbank Advisers", "Ironbridge Mortgages",
    "Wessex Intermediaries", "Granite Mortgage Group", "Elmwood Financial", "Marina Brokers",
    "Highfield Advisers", "Tower Hamlets Finance", "Peak District Mortgages", "Fenland Finance",
]
FIRM_WORDS_A = ["Oak", "Bridge", "Harbour", "Summit", "Meadow", "Anchor", "Lantern", "Compass", "Beacon", "Willow",
                "Granite", "Hollow", "Crescent", "Orchard", "Quarry", "Sterling", "Vantage", "Haven", "Ridge", "Fable"]
FIRM_WORDS_B = ["Mortgages", "Financial", "Advisers", "Property Finance", "Mortgage Services", "Finance", "Brokers",
                "Lending Solutions", "Mortgage Partners", "Capital"]
FIRST_NAMES = ["James", "Sarah", "Priya", "Tom", "Amelia", "Daniel", "Chloe", "Mohammed", "Grace", "Oliver",
               "Hannah", "Ravi", "Emily", "Jack", "Sophie", "Kwame", "Lucy", "George", "Aisha", "Ben"]
LAST_NAMES = ["Patel", "Smith", "Okafor", "Jones", "Williams", "Khan", "Taylor", "Brown", "Hughes", "Singh",
              "Evans", "Murphy", "Clarke", "Walker", "Robinson", "Wright", "Green", "Baker", "Hall", "Ahmed"]
POSTCODE_AREAS = {
    "London": ["E", "N", "SE", "SW", "W", "NW", "EC", "WC"], "South East": ["RG", "GU", "BN", "ME", "CT", "SL", "RH"],
    "East of England": ["CB", "CM", "IP", "NR", "CO", "SG"], "South West": ["BS", "BA", "EX", "PL", "TA", "GL"],
    "West Midlands": ["B", "CV", "WS", "WV", "DY"], "East Midlands": ["LE", "NG", "DE", "NN", "LN"],
    "North West": ["M", "L", "WA", "PR", "BL", "SK"], "Yorkshire and the Humber": ["LS", "S", "BD", "HU", "YO", "HX"],
    "North East": ["NE", "SR", "DH", "TS"], "Wales": ["CF", "SA", "NP", "LL"],
}

STRESS_FLOOR = C.STRESS_FLOOR_PCT
RENT_GROWTH = 0.04      # a year
HPI = {2023: -0.010, 2024: 0.025, 2025: 0.030, 2026: 0.020}   # illustrative house-price growth, a year


def month_starts(start: date, end: date):
    d = date(start.year, start.month, 1)
    while d <= end:
        yield d
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def bank_rate_on(d: date) -> float:
    r = C.BANK_RATE_PATH[0][1]
    for when, rate in C.BANK_RATE_PATH:
        if d >= when:
            r = rate
    return r


def hpi_index(d: date) -> float:
    """Cumulative house-price index from the start of the simulation (START = 1.0)."""
    idx, cur = 1.0, C.START
    while cur < d:
        nxt = min(d, date(cur.year + 1, 1, 1))
        idx *= (1 + HPI.get(cur.year, 0.02)) ** ((nxt - cur).days / 365.0)
        cur = nxt
    return idx


def stress_rate(pay_rate: float, fixed_years: int, term_type: str) -> float:
    if term_type == "fixed" and fixed_years >= 5:
        return pay_rate
    return max(pay_rate + C.STRESS_UPLIFT_PCT, STRESS_FLOOR)


def rental_cover(monthly_rent: float, loan: float, stress: float) -> float:
    return 100.0 * monthly_rent * 12 / (loan * stress / 100)


class Simulation:
    def __init__(self, seed: int = C.SEED, scale: float = 1.0, out: Path = Path("data")):
        self.rng = np.random.default_rng(seed)
        self.scale = scale
        self.out = Path(out)
        self.defects: list[dict] = []
        self.tables: dict[str, pd.DataFrame] = {}

    # ── helpers ────────────────────────────────────────────────────────────────
    def choice(self, options: dict):
        keys = list(options)
        p = np.array([options[k] for k in keys], dtype=float)
        return keys[self.rng.choice(len(keys), p=p / p.sum())]

    def dt_in_month(self, m: date) -> datetime:
        nxt = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        days = (nxt - m).days
        d = m + timedelta(days=int(self.rng.integers(0, days)))
        if d > C.END:
            d = C.END
        # office hours, weekdays more likely
        hour = int(self.rng.integers(8, 19))
        return datetime(d.year, d.month, d.day, hour, int(self.rng.integers(0, 60)))

    def days(self, lo: float, hi: float) -> timedelta:
        return timedelta(days=float(self.rng.uniform(lo, hi)))

    # ── reference data ─────────────────────────────────────────────────────────
    def make_brokers(self):
        n = max(40, int(400 * self.scale))
        rows = []
        for i in range(n):
            network = NETWORKS[int(self.rng.integers(0, len(NETWORKS)))] if self.rng.random() < 0.85 else "Directly authorised"
            region = self.choice({k: v[0] for k, v in C.REGIONS.items()})
            rows.append({
                "broker_id": f"B{i + 1:04d}",
                "firm_name": f"{FIRM_WORDS_A[int(self.rng.integers(0, 20))]} {FIRM_WORDS_B[int(self.rng.integers(0, 10))]}",
                "network": network,
                "region": region,
                "onboarded_date": (date(2018, 1, 1) + timedelta(days=int(self.rng.integers(0, 2900)))).isoformat(),
                "fca_firm_ref": int(self.rng.integers(100000, 999999)),
            })
        b = pd.DataFrame(rows)
        w = self.rng.lognormal(0, 0.9, size=n)
        self.broker_weights = w / w.sum()
        self.tables["brokers"] = b
        self.net_rent_brokers = set(b.loc[b.network == "Pennine Mortgage Network", "broker_id"])

    def make_products(self):
        prods = []
        for pid, rng_, pscope, bscope, term, fy, ltv, fee, purposes in C.PRODUCTS:
            prods.append({"product_id": pid, "product_range": rng_, "property_scope": pscope, "borrower_scope": bscope,
                          "term_type": term, "fixed_years": fy, "max_ltv_pct": ltv, "fee_pct": fee, "purposes": purposes,
                          "erc_applies": term == "fixed"})
        self.tables["products"] = pd.DataFrame(prods)
        # versioned rate cards
        cards = []
        for p in prods:
            d = C.START
            v = 0
            while d <= C.END:
                v += 1
                cards.append({"rate_card_id": f"{p['product_id']}-v{v:02d}", "product_id": p["product_id"],
                              "valid_from": d, "version": v,
                              **self.price(p, d)})
                d = d + timedelta(days=int(self.rng.integers(30, 110)))
        rc = pd.DataFrame(cards).sort_values(["product_id", "valid_from"]).reset_index(drop=True)
        rc["valid_to"] = rc.groupby("product_id")["valid_from"].shift(-1) - pd.Timedelta(days=1)
        rc["valid_from"] = pd.to_datetime(rc["valid_from"]).dt.date
        rc["valid_to"] = pd.to_datetime(rc["valid_to"]).dt.date
        self.tables["rate_cards"] = rc
        self.rate_cards = rc
        self._cards = {pid: [r for r in g.itertuples(index=False)] for pid, g in rc.groupby("product_id", sort=False)}

    def price(self, p: dict, d: date) -> dict:
        """Illustrative pricing: a proxy for swap rates plus loadings for fee, term, property type and LTV."""
        br = bank_rate_on(d)
        year_adj = {2023: 0.30, 2024: -0.30, 2025: -0.45, 2026: -0.35}[d.year]
        swap = br + year_adj + float(self.rng.normal(0, 0.08))
        if p["term_type"] == "tracker":
            margin = {65: 1.49, 75: 1.74 if p["fee_pct"] >= 3 else 2.24, 80: 2.49}[p["max_ltv_pct"]]
            if p["product_range"] == "Specialist":
                margin += 0.25
            return {"initial_rate_pct": None, "tracker_margin_pct": round(margin, 2), "reversion_margin_pct": 4.5}
        rate = swap + (0.9 if p["fixed_years"] >= 5 else 1.2)
        rate += {0.0: 1.0, 1.0: 0.6, 2.0: 0.35, 3.0: 0.15, 5.0: -0.35}[p["fee_pct"]]
        rate += {"standard": 0.0, "hmo_small": 0.30, "mufb_small": 0.45, "hmo_small,mufb_small": 0.40}[p["property_scope"]]
        rate += {65: -0.20, 75: 0.0, 80: 0.40}[p["max_ltv_pct"]]
        rate = float(np.clip(round(rate, 2), 3.09, 7.49))
        return {"initial_rate_pct": rate, "tracker_margin_pct": None, "reversion_margin_pct": 4.5}

    def card_at(self, product_id: str, d: date, previous: bool = False):
        cards = self._cards[product_id]            # sorted by valid_from
        row = cards[0]
        for i, c in enumerate(cards):
            if c.valid_from <= d:
                row = c
                idx = i
            else:
                break
        else:
            idx = len(cards) - 1
        if row.valid_from > d:
            idx = 0
        if previous and idx > 0:
            return cards[idx - 1]
        return row

    def pay_rate(self, card, d: date) -> float:
        if pd.isna(card.initial_rate_pct):
            return round(bank_rate_on(d) + float(card.tracker_margin_pct), 2)
        return float(card.initial_rate_pct)

    def make_funding_partners(self):
        rows = []
        for fp in C.FUNDING_PARTNERS:
            rows.append({**fp, "monthly_capacity_gbp": fp["monthly_capacity_gbp"] * self.scale,    # lines scale with volume
                         "line_start": fp["line_start"].isoformat(),
                         "line_end": fp["line_end"].isoformat() if fp["line_end"] else None})
        self.tables["funding_partners"] = pd.DataFrame(rows)

    # ── the pipeline ───────────────────────────────────────────────────────────
    def make_pipeline(self):
        products = self.tables["products"]
        brokers = self.tables["brokers"]
        dips, apps, hist, vals, offers, comps = [], [], [], [], [], []
        dip_n = app_n = val_n = off_n = comp_n = 0
        months = list(month_starts(C.START, C.END))
        for mi, m in enumerate(months):
            n = C.DIPS_PER_MONTH * self.scale * (1 + C.MONTHLY_GROWTH) ** mi * C.SEASONALITY[m.month]
            n = int(self.rng.poisson(n))
            for _ in range(n):
                dip_n += 1
                created = self.dt_in_month(m)
                broker = brokers.iloc[int(self.rng.choice(len(brokers), p=self.broker_weights))]
                region = self.choice({k: v[0] for k, v in C.REGIONS.items()})
                ptype = self.choice(C.PROPERTY_TYPES)
                purpose = self.choice(C.PURPOSES)
                btype = self.choice(C.BORROWER_TYPES)
                band = self.choice(C.TAX_BANDS_INDIVIDUAL) if btype == "individual" else "limited_company"
                portfolio = int(self.rng.choice([1, 2, 3, 4, 6, 8, 12, 18, 25], p=[.30, .18, .12, .10, .10, .08, .06, .04, .02]))
                base_val, base_yield = C.REGIONS[region][1], C.REGIONS[region][2]
                value = float(base_val * np.exp(self.rng.normal(0, 0.35)) * {"standard": 1.0, "hmo_small": 1.45, "mufb_small": 1.9}[ptype])
                value = round(value / 1000) * 1000
                gyield = base_yield + {"standard": 0, "hmo_small": 0.015, "mufb_small": 0.012}[ptype] + float(self.rng.normal(0, 0.006))
                rent = round(value * gyield / 12 / 10) * 10
                ltv_req = float(self.rng.choice([55, 60, 65, 70, 75, 80], p=[.08, .12, .18, .22, .32, .08]))
                loan = int(value * ltv_req / 100 // 500) * 500
                candidates = products[(products.purposes.str.contains(purpose)) & (products.property_scope.str.contains(ptype))
                                      & (products.max_ltv_pct >= ltv_req)]
                if candidates.empty:
                    result, product = "decline", None
                else:
                    product = candidates.iloc[int(self.rng.integers(0, len(candidates)))]
                    card = self.card_at(product.product_id, created.date())
                    pr = self.pay_rate(card, created.date())
                    icr = rental_cover(rent, loan, stress_rate(pr, int(product.fixed_years), product.term_type))
                    if icr < C.MIN_RENTAL_COVER[band]:
                        result = "decline" if self.rng.random() < 0.7 else "refer"
                    else:
                        result = "accept" if self.rng.random() < 0.93 else "refer"
                dip_id = f"D{dip_n:06d}"
                dips.append({"dip_id": dip_id, "broker_id": broker.broker_id, "created_at": created, "borrower_type": btype,
                             "tax_band": band, "property_type": ptype, "purpose": purpose, "region": region,
                             "postcode_area": POSTCODE_AREAS[region][int(self.rng.integers(0, len(POSTCODE_AREAS[region])))],
                             "portfolio_size": portfolio, "property_value_est": value, "loan_requested": loan,
                             "monthly_rent_est": rent, "ltv_requested_pct": ltv_req,
                             "product_id": None if product is None else product.product_id, "dip_result": result})
                if result != "accept" or self.rng.random() > 0.58:
                    continue
                # ── application
                app_n += 1
                mismatch_planted = False
                app_id = f"A{app_n:06d}"
                submitted = created + self.days(1, 21) if purpose != "product_transfer" else created + self.days(0.5, 5)
                if submitted.date() > C.END:
                    continue
                card = self.card_at(product.product_id, submitted.date())
                declared_rent = round(rent * float(self.rng.normal(1.0, 0.02)) / 5) * 5
                if broker.broker_id in self.net_rent_brokers:
                    declared_rent = round(declared_rent * 0.90 / 5) * 5          # defect: rent declared net of a 10% fee
                    self.defects.append({"defect_type": "rent_basis_net", "entity": "applications", "record_id": app_id,
                                         "detail": "declared_monthly_rent is net of a 10% management fee; policy uses the valuer's gross rent"})
                app = {"application_id": app_id, "dip_id": dip_id, "broker_id": broker.broker_id, "submitted_at": submitted,
                       "borrower_type": btype, "tax_band": band, "property_type": ptype, "purpose": purpose, "region": region,
                       "postcode_area": dips[-1]["postcode_area"], "portfolio_size": portfolio, "property_value": value,
                       "loan_amount": loan, "declared_monthly_rent": declared_rent, "product_id": product.product_id,
                       "rate_card_id": card.rate_card_id, "valuation_type_requested": "physical", "notes": "",
                       "status_current": "submitted", "completed_at": None}
                events = [("submitted", submitted)]
                # ── valuation
                val_n += 1
                instructed = submitted + self.days(1, 4)
                eligible = (purpose == "remortgage" and ptype in C.FEATURE_ELIGIBLE_PROPERTY_TYPES
                            and ltv_req <= C.FEATURE_MAX_LTV and portfolio <= C.FEATURE_MAX_PORTFOLIO)
                post_launch = submitted.date() >= C.FEATURE_LAUNCH
                if purpose == "product_transfer":
                    vtype = "avm"
                elif eligible and post_launch and self.rng.random() < C.FEATURE_AVM_TAKE_UP:
                    vtype = "avm"
                else:
                    vtype = "physical"
                app["valuation_type_requested"] = vtype
                app["feature_eligible"] = eligible
                if vtype == "avm":
                    received = instructed + self.days(*C.AVM_VALUATION_DAYS)
                else:
                    received = instructed + self.days(*C.PHYSICAL_VALUATION_DAYS)
                market_value = round(value * float(self.rng.normal(1.0, 0.025)) / 1000) * 1000
                assessed_rent = round(rent * float(self.rng.normal(1.0, 0.04)) / 5) * 5
                vals.append({"valuation_id": f"V{val_n:06d}", "application_id": app_id, "valuation_type": vtype,
                             "instructed_at": instructed, "received_at": received, "market_value": market_value,
                             "monthly_rent_assessed": assessed_rent, "property_type_assessed": ptype,
                             "provider": "AVM provider" if vtype == "avm" else f"Panel valuer {int(self.rng.integers(1, 9))}",
                             "fee_gbp": 0 if vtype == "avm" else int(self.rng.choice([300, 400, 500, 650]))})
                events += [("valuation_instructed", instructed), ("valuation_received", received)]
                # ── underwriting
                uw_days = float(self.rng.uniform(3, 8))
                if submitted.date() >= C.BACKGROUND_SPEEDUP_FROM:
                    uw_days = max(1.0, uw_days - C.BACKGROUND_SPEEDUP_DAYS)
                uw_start = received + self.days(0.2, 1.0)
                uw_end = uw_start + timedelta(days=uw_days)
                events.append(("underwriting_started", uw_start))
                pr = self.pay_rate(card, submitted.date())
                stress = stress_rate(pr, int(product.fixed_years), product.term_type)
                loan_final = min(loan, int(market_value * product.max_ltv_pct / 100 // 500) * 500)
                icr = rental_cover(assessed_rent, loan_final, stress)
                decline = icr < C.MIN_RENTAL_COVER[band] or self.rng.random() < 0.07
                if decline:
                    events.append(("declined", uw_end))
                    app["status_current"] = "declined"
                else:
                    off_n += 1
                    offered = uw_end + self.days(0.5, 3)
                    offer_card = card
                    offer_rate = pr
                    stale_from, stale_to, stale_range = C.DEFECTS["stale_rate_card"]
                    offer_id = f"O{off_n:06d}"
                    # Offers are priced on the card that was live when the case was submitted (a rate lock). During
                    # the planted window, Core offers are priced on the card that had already been replaced by then.
                    if stale_from <= offered.date() <= stale_to and product.product_range == stale_range:
                        prev = self.card_at(product.product_id, submitted.date(), previous=True)
                        if prev.rate_card_id != card.rate_card_id:
                            offer_card, offer_rate = prev, self.pay_rate(prev, submitted.date())
                            self.defects.append({"defect_type": "stale_rate_card", "entity": "offers", "record_id": offer_id,
                                                 "detail": f"offer priced on {prev.rate_card_id}, which {card.rate_card_id} had replaced before submission"})
                    offers.append({"offer_id": offer_id, "application_id": app_id, "offered_at": offered,
                                   "offer_expiry": offered + timedelta(days=90), "loan_amount": loan_final,
                                   "product_id": product.product_id, "rate_card_id": offer_card.rate_card_id,
                                   "initial_rate_pct": offer_rate, "stress_rate_pct": round(stress, 2),
                                   "ltv_pct": round(100 * loan_final / market_value, 1),
                                   "rental_cover_pct": round(rental_cover(assessed_rent, loan_final, stress), 1),
                                   "offer_accepted_at": None})
                    events.append(("offered", offered))
                    app["status_current"] = "offered"
                    withdraw_p = 0.16 - (C.FEATURE_TRUE_EFFECTS["avm_withdrawal_rate_reduction"] if vtype == "avm" and purpose != "product_transfer" else 0)
                    if self.rng.random() < withdraw_p:
                        events.append(("withdrawn", offered + self.days(3, 30)))
                        app["status_current"] = "withdrawn"
                    else:
                        accepted = offered + self.days(2, 12)
                        offers[-1]["offer_accepted_at"] = accepted
                        events.append(("offer_accepted", accepted))
                        app["status_current"] = "offer_accepted"
                        if self.rng.random() < 0.08:
                            events.append(("withdrawn", accepted + self.days(5, 40)))
                            app["status_current"] = "withdrawn"
                        else:
                            gap = {"purchase": (25, 70), "remortgage": (14, 40), "product_transfer": (3, 10)}[purpose]
                            funds = accepted + self.days(*gap)
                            comp_n += 1
                            comps.append({"completion_id": f"C{comp_n:06d}", "application_id": app_id, "funds_released_at": funds,
                                          "loan_amount": loan_final, "product_id": product.product_id,
                                          "rate_card_id": offer_card.rate_card_id, "initial_rate_pct": offer_rate,
                                          "fixed_years": int(product.fixed_years), "term_type": product.term_type,
                                          "market_value": market_value, "monthly_rent": assessed_rent,
                                          "solicitor": f"Panel solicitor {int(self.rng.integers(1, 12))}",
                                          "completion_fee_gbp": int(round(loan_final * product.fee_pct / 100))})
                            events.append(("completed", funds))
                            app["status_current"] = "completed"
                            app["completed_at"] = funds
                            if self.rng.random() < C.DEFECTS["completion_date_mismatch"]:
                                app["completed_at"] = accepted                          # defect: wrong definition
                                mismatch_planted = True
                # censor anything after the end of the period
                kept = [(s, t) for s, t in events if t.date() <= C.END]
                if len(kept) < len(events):
                    last = kept[-1][0]
                    app["status_current"] = {"submitted": "submitted", "valuation_instructed": "valuation_instructed",
                                             "valuation_received": "valuation_received", "underwriting_started": "underwriting",
                                             "offered": "offered", "offer_accepted": "offer_accepted"}.get(last, last)
                    if app["completed_at"] is not None and app["completed_at"].date() > C.END:
                        app["completed_at"] = None
                    if comps and comps[-1]["application_id"] == app_id and comps[-1]["funds_released_at"].date() > C.END:
                        comps.pop()
                    if offers and offers[-1]["application_id"] == app_id:
                        if offers[-1]["offered_at"].date() > C.END:
                            offers.pop()
                        elif offers[-1]["offer_accepted_at"] is not None and offers[-1]["offer_accepted_at"].date() > C.END:
                            offers[-1]["offer_accepted_at"] = None
                    if vals and vals[-1]["application_id"] == app_id and vals[-1]["instructed_at"].date() > C.END:
                        vals.pop()
                    elif vals and vals[-1]["application_id"] == app_id and vals[-1]["received_at"].date() > C.END:
                        vals[-1]["received_at"] = None
                if mismatch_planted and app["completed_at"] is not None:
                    self.defects.append({"defect_type": "completion_date_mismatch", "entity": "applications", "record_id": app_id,
                                         "detail": "completed_at holds the offer-accepted date, not the date funds were released"})
                for s, t in kept:
                    hist.append({"application_id": app_id, "status": s, "status_at": t})
                apps.append(app)
        self.tables["dips"] = pd.DataFrame(dips)
        self.tables["applications"] = pd.DataFrame(apps)
        self.tables["application_status_history"] = pd.DataFrame(hist)
        self.tables["valuations"] = pd.DataFrame(vals)
        self.tables["offers"] = pd.DataFrame(offers)
        self.tables["completions"] = pd.DataFrame(comps)

    # ── funding allocation ─────────────────────────────────────────────────────
    def make_allocations(self):
        comps = self.tables["completions"].merge(self.tables["applications"][["application_id", "property_type"]], on="application_id")
        comps = comps.merge(self.tables["products"][["product_id", "product_range", "max_ltv_pct"]], on="product_id")
        comps["month"] = pd.to_datetime(comps.funds_released_at).dt.to_period("M")
        rows = []
        over_months = {(y, m) for y, m in C.DEFECTS["partner_over_capacity"]}
        for month, grp in comps.sort_values("funds_released_at").groupby("month"):
            mstart = month.start_time.date()
            used = {fp["partner_id"]: 0.0 for fp in C.FUNDING_PARTNERS}
            for _, c in grp.iterrows():
                order = ["FP03", "FP02", "FP04", "FP01"]
                placed = None
                for pid in order:
                    fp = next(f for f in C.FUNDING_PARTNERS if f["partner_id"] == pid)
                    if fp["line_start"] > mstart or (fp["line_end"] and fp["line_end"] < mstart):
                        continue
                    if fp["scope"] == "core_only" and c.product_range != "Core":
                        continue
                    if fp["scope"] == "standard_75" and not (c.property_type == "standard" and c.max_ltv_pct <= 75):
                        continue
                    cap = fp["monthly_capacity_gbp"] * self.scale
                    if pid == "FP02" and (mstart.year, mstart.month) in over_months:
                        cap *= 1.15                                              # defect: allocated above the line
                    if used[pid] + c.loan_amount <= cap or pid == "FP01":
                        placed = pid
                        break
                used[placed] += c.loan_amount
                rows.append({"allocation_id": f"AL{len(rows) + 1:06d}", "completion_id": c.completion_id, "partner_id": placed,
                             "allocated_amount": c.loan_amount, "allocation_month": mstart.isoformat()})
                fp = next(f for f in C.FUNDING_PARTNERS if f["partner_id"] == placed)
                # The answer key lists every allocation that is actually over its line: the planted FP02 months, and any
                # month where the FP01 backstop (which takes whatever the others cannot) is itself pushed past its line.
                if used[placed] > fp["monthly_capacity_gbp"] * self.scale:
                    self.defects.append({"defect_type": "partner_over_capacity", "entity": "funding_allocations",
                                         "record_id": rows[-1]["allocation_id"],
                                         "detail": f"{placed} allocated {used[placed]:,.0f} against a line of {fp['monthly_capacity_gbp'] * self.scale:,.0f} in {mstart:%Y-%m}"})
        self.tables["funding_allocations"] = pd.DataFrame(rows)

    # ── servicing: loan book snapshots and product transfers ──────────────────
    def make_loan_book(self):
        comps = self.tables["completions"]
        alloc = self.tables["funding_allocations"][["completion_id", "partner_id"]]
        comps = comps.merge(alloc, on="completion_id", how="left")
        snaps, pts = [], []
        months = list(month_starts(C.START, C.END))
        hpi = {m: hpi_index(m) for m in months}
        ptype_of = self.tables["applications"].set_index("application_id")["property_type"].to_dict()
        prods = self.tables["products"]
        pt_products = {pt: prods[(prods.purposes == "product_transfer") & (prods.property_scope.str.contains(pt))]
                       for pt in C.PROPERTY_TYPES}
        for i, c in comps.reset_index(drop=True).iterrows():
            loan_id = f"L{i + 1:06d}"
            start = pd.Timestamp(c.funds_released_at).date()
            fixed_end = date(start.year + c.fixed_years, start.month, min(start.day, 28))
            arrears = 0
            status = "live"
            rate = float(c.initial_rate_pct)
            for m in months:
                if m < date(start.year, start.month, 1):
                    continue
                if m > C.END:
                    break
                # events at fixed-rate end
                if status == "live" and (m.year, m.month) == (fixed_end.year, fixed_end.month):
                    outcome = self.choice({"product_transfer": 0.60, "redeemed": 0.30, "reverted": 0.10})
                    decided = fixed_end - timedelta(days=int(self.rng.integers(5, 60)))
                    new_pid = None
                    new_card = None
                    if outcome == "product_transfer":
                        pt = pt_products[ptype_of[c.application_id]]
                        p = pt.iloc[int(self.rng.integers(0, len(pt)))]
                        card = self.card_at(p.product_id, fixed_end)
                        new_pid, new_card = p.product_id, card.rate_card_id
                        rate = self.pay_rate(card, fixed_end)
                        fixed_end = date(fixed_end.year + int(p.fixed_years), fixed_end.month, fixed_end.day)
                    elif outcome == "redeemed":
                        status = "redeemed"
                    else:
                        rate = bank_rate_on(fixed_end) + 4.5
                    maturity = fixed_end if outcome != "product_transfer" else fixed_end.replace(year=fixed_end.year - int(p.fixed_years))
                    pts.append({"product_transfer_id": f"PT{len(pts) + 1:06d}", "loan_id": loan_id, "maturity_date": maturity.isoformat(),
                                "outcome": outcome, "decided_at": decided.isoformat(), "new_product_id": new_pid, "new_rate_card_id": new_card})
                if status == "redeemed":
                    snaps.append({"snapshot_month": m.isoformat(), "loan_id": loan_id, "completion_id": c.completion_id,
                                  "partner_id": c.partner_id, "status": "redeemed", "balance": 0.0, "indexed_value": None,
                                  "ltv_current_pct": None, "monthly_rent": None, "pay_rate_pct": None,
                                  "rental_cover_current_pct": None, "arrears_months": None, "fixed_end_date": None})
                    break
                if self.rng.random() < 0.006 and m < fixed_end:          # early redemption
                    status = "redeemed"
                # arrears: enter, cure, or deepen
                if arrears == 0:
                    arrears = 1 if self.rng.random() < 0.004 else 0
                elif self.rng.random() < 0.30:
                    arrears = 0
                else:
                    arrears = min(arrears + 1, 6)
                years = (m - start).days / 365.0
                indexed = round(c.market_value * hpi[m] / hpi_index(start) / 1000) * 1000
                rent = round(c.monthly_rent * (1 + RENT_GROWTH) ** years / 5) * 5
                snaps.append({"snapshot_month": m.isoformat(), "loan_id": loan_id, "completion_id": c.completion_id,
                              "partner_id": c.partner_id, "status": status, "balance": float(c.loan_amount),
                              "indexed_value": indexed, "ltv_current_pct": round(100 * c.loan_amount / indexed, 1),
                              "monthly_rent": rent, "pay_rate_pct": round(rate, 2),
                              "rental_cover_current_pct": round(rental_cover(rent, c.loan_amount, rate), 1),
                              "arrears_months": arrears, "fixed_end_date": fixed_end.isoformat()})
        self.tables["loan_book_monthly"] = pd.DataFrame(snaps)
        self.tables["product_transfers"] = pd.DataFrame(pts)

    # ── portal events (JSON lines) ─────────────────────────────────────────────
    def make_portal_events(self):
        ev = []
        for d in self.tables["dips"].itertuples():
            t = pd.Timestamp(d.created_at)
            sid = f"S{abs(hash((d.dip_id, 'x'))) % 10**10:010d}"
            ev.append({"event_id": f"E{len(ev) + 1:07d}", "event_type": "dip_started", "event_at": (t - pd.Timedelta(minutes=int(self.rng.integers(3, 25)))).isoformat(),
                       "broker_id": d.broker_id, "dip_id": d.dip_id, "application_id": None,
                       "payload": {"session_id": sid, "device": self.choice({"desktop": .8, "mobile": .15, "tablet": .05}),
                                   "feature_flags": {"instant_avm": t.date() >= C.FEATURE_LAUNCH}}})
            ev.append({"event_id": f"E{len(ev) + 1:07d}", "event_type": "dip_completed", "event_at": t.isoformat(),
                       "broker_id": d.broker_id, "dip_id": d.dip_id, "application_id": None,
                       "payload": {"session_id": sid, "result": d.dip_result, "feature_flags": {"instant_avm": t.date() >= C.FEATURE_LAUNCH}}})
        for a in self.tables["applications"].itertuples():
            t = pd.Timestamp(a.submitted_at)
            flag = t.date() >= C.FEATURE_LAUNCH
            if a.purpose == "remortgage" and flag and a.feature_eligible:
                ev.append({"event_id": f"E{len(ev) + 1:07d}", "event_type": "avm_option_shown", "event_at": (t - pd.Timedelta(minutes=4)).isoformat(),
                           "broker_id": a.broker_id, "dip_id": a.dip_id, "application_id": a.application_id,
                           "payload": {"feature_flags": {"instant_avm": True}, "eligible": True}})
                if a.valuation_type_requested == "avm":
                    ev.append({"event_id": f"E{len(ev) + 1:07d}", "event_type": "avm_option_selected", "event_at": (t - pd.Timedelta(minutes=2)).isoformat(),
                               "broker_id": a.broker_id, "dip_id": a.dip_id, "application_id": a.application_id,
                               "payload": {"feature_flags": {"instant_avm": True}}})
            ev.append({"event_id": f"E{len(ev) + 1:07d}", "event_type": "application_submitted", "event_at": t.isoformat(),
                       "broker_id": a.broker_id, "dip_id": a.dip_id, "application_id": a.application_id,
                       "payload": {"feature_flags": {"instant_avm": flag}, "documents": int(self.rng.integers(2, 9))}})
        self.portal_events = ev

    # ── planted defects that change existing rows ──────────────────────────────
    def plant_defects(self):
        apps = self.tables["applications"]
        hist = self.tables["application_status_history"]
        vals = self.tables["valuations"]
        # duplicate applications (broker resubmissions)
        n_dup = int(len(apps) * C.DEFECTS["duplicate_application"])
        src = apps.sample(n=n_dup, random_state=int(self.rng.integers(0, 2**31)))
        dups, dup_hist = [], []
        next_id = int(apps.application_id.str[1:].astype(int).max())     # ids are not dense: some were skipped
        for _, a in src.iterrows():
            next_id += 1
            new_id = f"A{next_id:06d}"
            d = a.copy()
            d["application_id"] = new_id
            d["submitted_at"] = a.submitted_at + self.days(0.1, 2.5)
            d["status_current"] = "withdrawn" if self.rng.random() < 0.7 else "submitted"
            d["completed_at"] = None
            d["notes"] = "Resubmitted - broker could not see original case"
            dups.append(d)
            dup_hist.append({"application_id": new_id, "status": "submitted", "status_at": d["submitted_at"]})
            if d["status_current"] == "withdrawn":
                dup_hist.append({"application_id": new_id, "status": "withdrawn", "status_at": d["submitted_at"] + self.days(1, 10)})
            self.defects.append({"defect_type": "duplicate_application", "entity": "applications", "record_id": new_id,
                                 "detail": f"resubmission of {a.application_id} (same DIP, broker, property value and loan)"})
        apps = pd.concat([apps, pd.DataFrame(dups).astype(apps.dtypes.to_dict(), errors="ignore")], ignore_index=True) if dups else apps
        hist = pd.concat([hist, pd.DataFrame(dup_hist)], ignore_index=True)
        # status timestamps out of order
        both = hist[hist.status.isin(["valuation_instructed", "valuation_received"])].groupby("application_id").status.nunique()
        cand = both[both == 2].index.to_numpy()
        n_swap = int(len(cand) * C.DEFECTS["status_out_of_order"])
        for app_id in self.rng.choice(cand, size=n_swap, replace=False):
            i1 = hist.index[(hist.application_id == app_id) & (hist.status == "valuation_instructed")][0]
            i2 = hist.index[(hist.application_id == app_id) & (hist.status == "valuation_received")][0]
            hist.loc[i1, "status_at"], hist.loc[i2, "status_at"] = hist.loc[i2, "status_at"], hist.loc[i1, "status_at"]
            self.defects.append({"defect_type": "status_out_of_order", "entity": "application_status_history", "record_id": app_id,
                                 "detail": "valuation_received is stamped before valuation_instructed"})
        # AVM on ineligible properties
        physical = vals[(vals.valuation_type == "physical")].merge(apps[["application_id", "property_type", "loan_amount", "property_value"]], on="application_id")
        inel = physical[(physical.property_type == "mufb_small") | (100 * physical.loan_amount / physical.property_value > C.FEATURE_MAX_LTV)]
        pick = inel.sample(n=min(C.DEFECTS["avm_ineligible"], len(inel)), random_state=int(self.rng.integers(0, 2**31)))
        for vid in pick.valuation_id:
            i = vals.index[vals.valuation_id == vid][0]
            vals.loc[i, "valuation_type"] = "avm"
            vals.loc[i, "provider"] = "AVM provider"
            vals.loc[i, "fee_gbp"] = 0
            self.defects.append({"defect_type": "avm_ineligible", "entity": "valuations", "record_id": vid,
                                 "detail": "automated valuation on a property outside AVM policy (multi-unit block or LTV above 75%)"})
        # PII in free-text notes
        pick = apps.sample(n=C.DEFECTS["pii_in_notes"], random_state=int(self.rng.integers(0, 2**31))).index
        for i in pick:
            name = f"{FIRST_NAMES[int(self.rng.integers(0, 20))]} {LAST_NAMES[int(self.rng.integers(0, 20))]}"
            apps.loc[i, "notes"] = f"Spoke to Mr {name} about the rent figure, borrower confirms by phone"
            self.defects.append({"defect_type": "pii_in_notes", "entity": "applications", "record_id": apps.loc[i, "application_id"],
                                 "detail": "borrower's full name typed into free-text notes"})
        # orphan broker ids
        # Planted defects are kept independent so each one can be scored on its own: an orphaned broker id is never put
        # on a resubmission pair (the pair is matched on broker) or on a net-rent broker (the network is matched on broker).
        entangled = set(src.application_id) | {d["application_id"] for d in dups}
        pool = apps[~apps.application_id.isin(entangled) & ~apps.broker_id.isin(self.net_rent_brokers)]
        pick = pool.sample(n=C.DEFECTS["orphan_broker"], random_state=int(self.rng.integers(0, 2**31))).index
        for k, i in enumerate(pick):
            apps.loc[i, "broker_id"] = f"B9{900 + k:03d}"
            self.defects.append({"defect_type": "orphan_broker", "entity": "applications", "record_id": apps.loc[i, "application_id"],
                                 "detail": "broker_id not present in the broker file"})
        # non-positive loan amounts (on cases that never reached offer)
        never = apps[apps.status_current.isin(["submitted", "declined", "withdrawn"]) & ~apps.application_id.isin(self.tables["offers"].application_id)]
        pick = never.sample(n=C.DEFECTS["nonpositive_loan"], random_state=int(self.rng.integers(0, 2**31))).index
        for i in pick:
            apps.loc[i, "loan_amount"] = 0 if self.rng.random() < 0.5 else -float(apps.loc[i, "loan_amount"])
            self.defects.append({"defect_type": "nonpositive_loan", "entity": "applications", "record_id": apps.loc[i, "application_id"],
                                 "detail": "loan amount of zero or negative"})
        self.tables["applications"] = apps
        self.tables["application_status_history"] = hist
        self.tables["valuations"] = vals

    # ── output ─────────────────────────────────────────────────────────────────
    def write(self):
        raw = self.out / "raw"
        gt = self.out / "ground_truth"
        raw.mkdir(parents=True, exist_ok=True)
        gt.mkdir(parents=True, exist_ok=True)
        for name, df in self.tables.items():
            df = df.copy()
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]) or df[col].map(lambda x: isinstance(x, datetime)).any():
                    df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
            if "feature_eligible" in df.columns:
                df = df.drop(columns=["feature_eligible"])      # eligibility is derived in dbt, not exported
            df.to_csv(raw / f"{name}.csv", index=False)
        with open(raw / "portal_events.jsonl", "w") as f:
            for e in self.portal_events:
                f.write(json.dumps(e) + "\n")
        pd.DataFrame(self.defects).to_csv(gt / "defects.csv", index=False)
        with open(gt / "feature_effect.json", "w") as f:
            json.dump({
                "launch_date": C.FEATURE_LAUNCH.isoformat(),
                "eligible": {"purpose": "remortgage", "property_types": list(C.FEATURE_ELIGIBLE_PROPERTY_TYPES),
                             "max_ltv_pct": C.FEATURE_MAX_LTV, "max_portfolio_size": C.FEATURE_MAX_PORTFOLIO},
                "avm_take_up": C.FEATURE_AVM_TAKE_UP,
                "true_effects": C.FEATURE_TRUE_EFFECTS,
                "expected_effect_on_eligible_group": {
                    "days_to_offer": -C.FEATURE_AVM_TAKE_UP * C.FEATURE_TRUE_EFFECTS["avm_valuation_days_saved"],
                    "withdrawal_rate": -C.FEATURE_AVM_TAKE_UP * C.FEATURE_TRUE_EFFECTS["avm_withdrawal_rate_reduction"]},
                "background_change_affecting_everyone": {"from": C.BACKGROUND_SPEEDUP_FROM.isoformat(),
                                                         "underwriting_days_saved": C.BACKGROUND_SPEEDUP_DAYS},
            }, f, indent=2)

    def run(self):
        self.make_brokers()
        self.make_products()
        self.make_funding_partners()
        self.make_pipeline()
        self.make_allocations()
        self.make_loan_book()
        self.make_portal_events()
        self.plant_defects()
        self.write()
        return {k: len(v) for k, v in self.tables.items()} | {"portal_events": len(self.portal_events), "defects": len(self.defects)}
