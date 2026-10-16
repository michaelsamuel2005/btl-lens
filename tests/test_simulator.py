"""Unit tests for the simulator's building blocks and its determinism."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from simulate import config as C
from simulate.generate import Simulation, bank_rate_on, hpi_index, rental_cover, stress_rate


def test_stress_rate_policy():
    assert stress_rate(4.0, 2, "fixed") == 6.0          # pay rate + 2, above the 5.5 floor
    assert stress_rate(3.0, 2, "fixed") == 5.5          # floor applies
    assert stress_rate(4.8, 5, "fixed") == 4.8          # five-year fixes are stressed at the pay rate
    assert stress_rate(5.2, 2, "tracker") == 7.2


def test_rental_cover_formula():
    # £1,200 a month on a £200,000 loan stressed at 6%: 14,400 / 12,000 = 120%
    assert rental_cover(1200, 200_000, 6.0) == pytest.approx(120.0)


def test_bank_rate_path_is_a_step_function():
    assert bank_rate_on(date(2023, 1, 1)) == 3.50
    assert bank_rate_on(date(2023, 8, 3)) == 5.25
    assert bank_rate_on(date(2023, 8, 2)) == 5.00
    assert bank_rate_on(date(2026, 9, 30)) == 3.25


def test_hpi_index_compounds_from_start():
    assert hpi_index(C.START) == 1.0
    assert hpi_index(date(2024, 1, 1)) == pytest.approx(1 + C.HPI[2023] if hasattr(C, "HPI") else 0.99, rel=0.02)


def test_simulation_is_deterministic(tmp_path: Path):
    a = Simulation(seed=7, scale=0.05, out=tmp_path / "a").run()
    b = Simulation(seed=7, scale=0.05, out=tmp_path / "b").run()
    assert a == b
    fa = pd.read_csv(tmp_path / "a" / "raw" / "applications.csv")
    fb = pd.read_csv(tmp_path / "b" / "raw" / "applications.csv")
    pd.testing.assert_frame_equal(fa, fb)


def test_every_planted_defect_names_a_real_record(tmp_path: Path):
    Simulation(seed=3, scale=0.08, out=tmp_path).run()
    raw = tmp_path / "raw"
    ids = {
        "applications": set(pd.read_csv(raw / "applications.csv").application_id),
        "offers": set(pd.read_csv(raw / "offers.csv").offer_id),
        "valuations": set(pd.read_csv(raw / "valuations.csv").valuation_id),
        "funding_allocations": set(pd.read_csv(raw / "funding_allocations.csv").allocation_id),
        "application_status_history": set(pd.read_csv(raw / "application_status_history.csv").application_id),
    }
    defects = pd.read_csv(tmp_path / "ground_truth" / "defects.csv")
    assert set(defects.defect_type) == set(C.DEFECTS)
    for row in defects.itertuples():
        assert row.record_id in ids[row.entity], (row.defect_type, row.record_id)


def test_feature_eligibility_and_effect_are_recorded(tmp_path: Path):
    Simulation(seed=5, scale=0.05, out=tmp_path).run()
    import json
    fx = json.loads((tmp_path / "ground_truth" / "feature_effect.json").read_text())
    assert fx["launch_date"] == C.FEATURE_LAUNCH.isoformat()
    assert fx["expected_effect_on_eligible_group"]["days_to_offer"] == pytest.approx(-C.FEATURE_AVM_TAKE_UP * C.FEATURE_TRUE_EFFECTS["avm_valuation_days_saved"])
