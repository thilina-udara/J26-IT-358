"""
Tests for Yield Prediction API and Linear SHAP Explainability

What this test file checks:
1. Model loading and verified empirical training averages.
2. Mathematical consistency: baseline yield + weather shock = final predicted yield.
3. Maize damping factor (gamma = 0.0) prevents macro fertilizer shortage misattribution.
4. Complete omission of Bethma or cultivation planning advice.
5. Optional growth stage handling (Mode A vs Mode B).
6. Strict use of Pumpkin (DCS category) and rejection of unsupported crops (422 error).
"""

import sys
import os
import unittest
import numpy as np

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app
from app.routes.yield_prediction import load_hybrid_model, _FEATURE_MEANS, _EXPECTED_SHOCK_BASELINE
from app.schemas.yield_prediction import (
    YieldPredictionRequest,
    DistrictEnum,
    SeasonEnum,
    CropEnum,
    IrrigationZoneEnum
)


class TestYieldPredictionAPI(unittest.TestCase):
    """Rigorous test suite covering model inference, Linear SHAP consistency, boundary safety, and error handling."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.artifact = load_hybrid_model()

    def test_01_model_artifact_loaded_successfully(self):
        """Verify deployed artifact contains all 40 required features, Ridge model, and damping factors."""
        self.assertIn("shock_ridge_model", self.artifact)
        self.assertIn("feature_columns", self.artifact)
        self.assertIn("crop_shock_damping", self.artifact)
        self.assertEqual(len(self.artifact["feature_columns"]), 40)
        self.assertEqual(len(self.artifact["num_cols"]), 4)
        self.assertEqual(len(_FEATURE_MEANS), 40)
        self.assertAlmostEqual(_EXPECTED_SHOCK_BASELINE, 0.292315, places=4)

    def test_02_prediction_and_explanation_consistency(self):
        """Verify exact mathematical reconciliation between baseline, Linear SHAP shock, and final yield."""
        payload = {
            "district": "Anuradhapura",
            "season": "Maha",
            "crop_name": "Tomato",
            "irrigation_zone_type": "Major Irrigation",
            "rainfall_growing_season_total_mm": 950.0,
            "temp_growing_season_mean_c": 27.5,
            "soil_moisture_growing_season_min": 0.28,
            "spi3_growing_season_worst": 0.35,
            "current_growth_stage": None
        }
        response = self.client.post("/api/v1/predict-yield-deficit", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify base response fields
        self.assertEqual(data["district"], "Anuradhapura")
        self.assertEqual(data["crop_name"], "Tomato")
        self.assertGreater(data["predicted_yield_mt_ha"], 0.0)
        
        # Verify XAI Breakdown
        xai = data["explainability"]
        self.assertTrue(xai["is_explanation_consistent"])
        
        baseline = xai["historical_baseline_yield_mt_ha"]
        shock = xai["total_climate_shock_impact_mt_ha"]
        adj = xai["clamping_adjustment_mt_ha"]
        reconciled = xai["final_reconciled_yield_mt_ha"]
        predicted = data["predicted_yield_mt_ha"]
        
        # Exact mathematical identity: Reconciled = Baseline + Shock + Clamping Adjustment
        self.assertAlmostEqual(reconciled, baseline + shock + adj, places=4)
        self.assertAlmostEqual(reconciled, predicted, places=2)
        
        # Verify all 4 verified climate features are attributed
        climate_attrs = xai["climate_feature_attributions"]
        self.assertEqual(len(climate_attrs), 4)
        feature_names = {a["feature_name"] for a in climate_attrs}
        expected_climate = {
            "rainfall_growing_season_total_mm",
            "temp_growing_season_mean_c",
            "soil_moisture_growing_season_min",
            "spi3_growing_season_worst"
        }
        self.assertEqual(feature_names, expected_climate)

    def test_03_maize_shock_damping_prevents_macro_misattribution(self):
        """Verify Maize damping factor (gamma=0.0) zeroes out climate shock attribution during macro crisis."""
        payload = {
            "district": "Monaragala",
            "season": "Maha",
            "crop_name": "Maize",
            "irrigation_zone_type": "Minor / Rainfed",
            "rainfall_growing_season_total_mm": 350.0,
            "temp_growing_season_mean_c": 30.5,
            "soil_moisture_growing_season_min": 0.16,
            "spi3_growing_season_worst": -1.65,
            "current_growth_stage": None
        }
        response = self.client.post("/api/v1/predict-yield-deficit", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        xai = data["explainability"]
        
        self.assertEqual(xai["crop_damping_factor"], 0.0)
        self.assertEqual(xai["total_climate_shock_impact_mt_ha"], 0.0)
        
        # All damped attributions for Maize must be exactly 0.0
        for attr in xai["climate_feature_attributions"]:
            self.assertEqual(attr["damped_attribution_mt_ha"], 0.0)
            self.assertEqual(attr["impact_direction"], "NEUTRAL")

    def test_04_no_bethma_or_cultivation_planning_in_advisories(self):
        """Verify strict removal of Bethma and cultivation planning recommendations under severe drought."""
        payload = {
            "district": "Puttalam",
            "season": "Yala",
            "crop_name": "Chilli",
            "irrigation_zone_type": "Minor / Rainfed",
            "rainfall_growing_season_total_mm": 180.0,
            "temp_growing_season_mean_c": 32.5,
            "soil_moisture_growing_season_min": 0.12,
            "spi3_growing_season_worst": -2.10,
            "current_growth_stage": None
        }
        response = self.client.post("/api/v1/predict-yield-deficit", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        advisories_text = " ".join(data["actionable_advisories"]).lower()
        summary_text = data["risk_summary"].lower()
        
        # Non-negotiable check: Zero Bethma mentions
        self.assertNotIn("bethma", advisories_text)
        self.assertNotIn("bethma", summary_text)
        
        # Non-negotiable check: Zero sowing date or planting calendar management
        self.assertNotIn("sowing date", advisories_text)
        self.assertNotIn("planting calendar", advisories_text)

    def test_05_optional_current_growth_stage_handling(self):
        """Verify Mode A (None) vs Mode B (Provided) handling without stage inference."""
        # Test Mode A: None provided
        payload_mode_a = {
            "district": "Matale",
            "season": "Yala",
            "crop_name": "Green Gram",
            "irrigation_zone_type": "Minor / Rainfed",
            "rainfall_growing_season_total_mm": 450.0,
            "temp_growing_season_mean_c": 29.0,
            "soil_moisture_growing_season_min": 0.22,
            "spi3_growing_season_worst": -0.80,
            "current_growth_stage": None
        }
        resp_a = self.client.post("/api/v1/predict-yield-deficit", json=payload_mode_a)
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_a.json()["growth_stage_evaluated"], "General Whole-Season Sensitivity Profile")
        
        # Test Mode B: Upstream stage provided
        payload_mode_b = payload_mode_a.copy()
        payload_mode_b["current_growth_stage"] = "Pod Setting"
        resp_b = self.client.post("/api/v1/predict-yield-deficit", json=payload_mode_b)
        self.assertEqual(resp_b.status_code, 200)
        self.assertEqual(resp_b.json()["growth_stage_evaluated"], "Upstream Stage: Pod Setting")
        self.assertIn("Pod Setting", resp_b.json()["risk_summary"])

    def test_06_pumpkin_crop_scope_and_naming(self):
        """Verify Pumpkin is accepted and strictly named Pumpkin (DCS classification)."""
        payload = {
            "district": "Hambantota",
            "season": "Maha",
            "crop_name": "Pumpkin",
            "irrigation_zone_type": "Minor / Rainfed",
            "rainfall_growing_season_total_mm": 600.0,
            "temp_growing_season_mean_c": 28.0,
            "soil_moisture_growing_season_min": 0.24,
            "spi3_growing_season_worst": -0.20
        }
        response = self.client.post("/api/v1/predict-yield-deficit", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["crop_name"], "Pumpkin")

    def test_07_invalid_inputs_rejected_with_422(self):
        """Verify Pydantic input validation blocks unapproved crops, districts, and physical extremes."""
        # Unapproved crop
        bad_crop = {
            "district": "Ampara",
            "season": "Maha",
            "crop_name": "Ash Pumpkin",  # Strictly excluded
            "irrigation_zone_type": "Minor / Rainfed",
            "rainfall_growing_season_total_mm": 500.0,
            "temp_growing_season_mean_c": 28.0,
            "soil_moisture_growing_season_min": 0.25,
            "spi3_growing_season_worst": 0.0
        }
        resp = self.client.post("/api/v1/predict-yield-deficit", json=bad_crop)
        self.assertEqual(resp.status_code, 422)
        
        # Negative rainfall
        bad_rain = bad_crop.copy()
        bad_rain["crop_name"] = "Maize"
        bad_rain["rainfall_growing_season_total_mm"] = -10.0
        resp = self.client.post("/api/v1/predict-yield-deficit", json=bad_rain)
        self.assertEqual(resp.status_code, 422)
        
        # Impossible soil moisture
        bad_sm = bad_crop.copy()
        bad_sm["crop_name"] = "Maize"
        bad_sm["soil_moisture_growing_season_min"] = 1.80  # Above physical saturation
        resp = self.client.post("/api/v1/predict-yield-deficit", json=bad_sm)
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
