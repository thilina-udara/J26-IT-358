"""
Unit Tests for Candidate Model 1A v3 Flood Early Warning Engine
Component 04: AI-Powered Climate Early Warning DSS
"""

import pytest
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pipelines.flood_early_warning_v3_engine import predict_flood_early_warning_v3, OFFICIAL_DISTRICTS


def test_flood_v3_normal_weather():
    """Verify normal conditions return Tier 0 Normal."""
    res = predict_flood_early_warning_v3(
        district="Anuradhapura",
        rainfall_1d_mm=5.0,
        rainfall_3d_sum_mm=10.0,
        rainfall_7d_sum_mm=20.0,
        rainfall_14d_sum_mm=40.0,
        antecedent_precip_index=15.0,
        upstream_rainfall_3d_mm=0.0
    )
    assert res["alert_tier"] == "TIER_0_NORMAL"
    assert res["alert_color"] == "GREEN"
    assert res["calibrated_flood_probability"] < 0.110


def test_flood_v3_severe_surge():
    """Verify extreme rainfall event triggers Warning alert."""
    res = predict_flood_early_warning_v3(
        district="Batticaloa",
        rainfall_1d_mm=34.43,
        rainfall_3d_sum_mm=61.05,
        rainfall_7d_sum_mm=95.58,
        rainfall_14d_sum_mm=209.18,
        antecedent_precip_index=103.24,
        temp_mean_14d_c=27.4,
        temp_max_14d_peak_c=28.87,
        humidity_mean_14d_pct=85.0,
        soil_moisture_topsoil_m3_m3=0.399
    )
    assert res["alert_tier"] == "TIER_2_WARNING"
    assert res["alert_color"] == "RED"
    assert res["calibrated_flood_probability"] >= 0.160
    assert "Advance Warning Active" in res["actionable_lead_time"]


def test_flood_v3_invalid_district():
    """Verify invalid district raises ValueError."""
    with pytest.raises(ValueError):
        predict_flood_early_warning_v3(
            district="Atlantis",
            rainfall_1d_mm=10.0,
            rainfall_3d_sum_mm=20.0,
            rainfall_7d_sum_mm=30.0,
            rainfall_14d_sum_mm=40.0,
            antecedent_precip_index=10.0
        )
