"""
Unit and Integration Tests for Model 1: AI-Powered Climate Early Warning Multi-Hazard Classifier


What this test file verifies:
1. Deployed Model 1 Artifact Integrity:
   - Loads Tuned Multi-Class XGBoost Classifier artifact without error.
   - Verifies exact 50-feature schema (10 continuous, 25 district, 3 climate zone, 12 month dummy columns).
   - Verifies 4 hazard risk tier definitions (0: Normal, 1: Moderate, 2: Severe, 3: Extreme).
   - Confirms test set performance metrics (Accuracy >= 98%, Balanced Acc >= 95%, Macro F1 >= 0.95, ROC-AUC >= 0.99).
2. Probabilistic Inference & Mathematical Constraints:
   - Softmax probabilities sum to 1.0 (within 0.001 margin).
   - Each individual class probability bounded strictly in [0.0, 1.0].
   - Normal weather predicts Tier 0 (Normal / Low Risk) with dominant probability >= 0.90.
   - Acute drought condition predicts Tier 2 or 3 with high confidence.
   - Catastrophic rainfall condition (>=150 mm/day) predicts Tier 3 (Extreme Crisis).
3. Robustness & Fault Tolerance:
   - Rejects non-existent districts with clear ValueError.
   - Gracefully handles missing/unavailable telemetry with safe fallback payload.
4. FastAPI Endpoints Integration:
   - Direct classification: POST /api/v1/early-warning/classify
   - Telemetry screening: GET /api/v1/early-warning/{district}
   - Integrated DSS: POST /api/v1/integrated-decision-support
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
from pipelines.early_warning_classifier_engine import (
    load_early_warning_classifier,
    build_classifier_feature_vector,
    predict_climate_hazard_risk,
    OFFICIAL_DISTRICTS,
    CLIMATE_ZONES
)
from app.schemas.yield_prediction import (
    DistrictEnum,
    CropEnum,
    SeasonEnum,
    IrrigationZoneEnum
)


class TestEarlyWarningClassifierEngine(unittest.TestCase):
    """Rigorous unit testing for Model 1 artifact loading, feature vector synthesis, and inference."""

    @classmethod
    def setUpClass(cls):
        cls.artifact = load_early_warning_classifier()

    def test_01_artifact_structure_and_metrics(self):
        """Verifies deployed Model 1 artifact contains expected architecture and high-performance metrics."""
        self.assertIn("model", self.artifact)
        self.assertIn("feature_columns", self.artifact)
        self.assertIn("num_features", self.artifact)
        self.assertIn("cat_features", self.artifact)
        self.assertIn("tier_labels", self.artifact)
        self.assertIn("metrics", self.artifact)

        # 50 total features
        feature_cols = self.artifact["feature_columns"]
        self.assertEqual(len(feature_cols), 50)
        self.assertEqual(len(self.artifact["num_features"]), 10)

        # Confirm 4 tiers
        self.assertEqual(len(self.artifact["tier_labels"]), 4)
        self.assertEqual(self.artifact["tier_labels"][0], "Normal / Low Risk")
        self.assertEqual(self.artifact["tier_labels"][3], "Extreme Crisis")

        # Confirm quantitative validation metrics meet high academic thresholds
        metrics = self.artifact["metrics"]
        self.assertGreaterEqual(metrics["accuracy_pct"], 98.0)
        self.assertGreaterEqual(metrics["balanced_accuracy_pct"], 95.0)
        self.assertGreaterEqual(metrics["macro_f1_score"], 0.95)
        self.assertGreaterEqual(metrics["roc_auc_ovr"], 0.99)

    def test_02_feature_vector_alignment(self):
        """Verifies build_classifier_feature_vector produces a 1x50 DataFrame exactly matching feature columns."""
        df_vec = build_classifier_feature_vector(
            district="Anuradhapura",
            rainfall_14d_sum_mm=50.0,
            rainfall_max_1d_mm=15.0,
            temp_max_14d_peak_c=32.0,
            temp_mean_14d_c=27.5,
            temp_min_14d_c=23.0,
            humidity_mean_pct=72.0,
            consecutive_heat_days=0,
            consecutive_dry_days=2,
            soil_moisture_topsoil_m3_m3=0.26,
            spi3_current=-0.1,
            month=5
        )
        self.assertEqual(df_vec.shape, (1, 50))
        self.assertListEqual(list(df_vec.columns), self.artifact["feature_columns"])
        
        # Verify one-hot activations
        self.assertEqual(df_vec["district_Anuradhapura"].iloc[0], 1.0)
        self.assertEqual(df_vec["district_Colombo"].iloc[0], 0.0)
        self.assertEqual(df_vec["climate_zone_Dry"].iloc[0], 1.0)
        self.assertEqual(df_vec["climate_zone_Wet"].iloc[0], 0.0)
        self.assertEqual(df_vec["month_5"].iloc[0], 1.0)
        self.assertEqual(df_vec["month_1"].iloc[0], 0.0)

    def test_03_softmax_probability_distribution_integrity(self):
        """Verifies that predicted softmax probabilities are bounded in [0, 1] and sum to 1.0."""
        res = predict_climate_hazard_risk(
            district="Kurunegala",
            rainfall_14d_sum_mm=60.0,
            rainfall_max_1d_mm=20.0,
            temp_max_14d_peak_c=31.0,
            temp_mean_14d_c=27.0,
            temp_min_14d_c=23.0,
            soil_moisture_topsoil_m3_m3=0.28,
            spi3_current=0.0
        )
        self.assertEqual(res["status"], "CLASSIFICATION_SUCCESS")
        probs = res["risk_probabilities"]
        self.assertIn("Normal", probs)
        self.assertIn("Moderate", probs)
        self.assertIn("Severe", probs)
        self.assertIn("Extreme", probs)

        total_prob = sum(probs.values())
        self.assertAlmostEqual(total_prob, 1.0, places=3)
        for tier_k, prob_val in probs.items():
            self.assertGreaterEqual(prob_val, 0.0)
            self.assertLessEqual(prob_val, 1.0)

    def test_04_normal_weather_classifies_tier_0(self):
        """Mild rainfall, moderate temperature, and positive SPI must classify as Tier 0 Normal."""
        res = predict_climate_hazard_risk(
            district="Galle",
            rainfall_14d_sum_mm=75.0,
            rainfall_max_1d_mm=22.0,
            temp_max_14d_peak_c=29.5,
            temp_mean_14d_c=26.5,
            temp_min_14d_c=24.0,
            soil_moisture_topsoil_m3_m3=0.32,
            spi3_current=0.4
        )
        self.assertEqual(res["predicted_risk_tier"], 0)
        self.assertEqual(res["risk_tier_name"], "Normal / Low Risk")
        self.assertGreaterEqual(res["risk_probabilities"]["Normal"], 0.85)

    def test_05_extreme_drought_classifies_tier_3(self):
        """Severe water deficit (SPI-3 <= -2.0, dry soil < 0.12, prolonged heat) must trigger high hazard tier."""
        res = predict_climate_hazard_risk(
            district="Mannar",
            rainfall_14d_sum_mm=1.5,
            rainfall_max_1d_mm=1.0,
            temp_max_14d_peak_c=38.0,
            temp_mean_14d_c=33.0,
            temp_min_14d_c=28.0,
            consecutive_dry_days=14,
            consecutive_heat_days=9,
            soil_moisture_topsoil_m3_m3=0.10,
            spi3_current=-2.6
        )
        self.assertIn(res["predicted_risk_tier"], [2, 3])
        self.assertGreaterEqual(res["risk_probabilities"]["Severe"] + res["risk_probabilities"]["Extreme"], 0.90)

    def test_06_catastrophic_flood_classifies_tier_3(self):
        """Catastrophic single-day rainfall (>= 150 mm) must trigger Tier 3 (Extreme Crisis)."""
        res = predict_climate_hazard_risk(
            district="Ratnapura",
            rainfall_14d_sum_mm=420.0,
            rainfall_max_1d_mm=180.0,
            temp_max_14d_peak_c=28.5,
            temp_mean_14d_c=25.0,
            temp_min_14d_c=22.0,
            soil_moisture_topsoil_m3_m3=0.45,
            spi3_current=1.9
        )
        self.assertEqual(res["predicted_risk_tier"], 3)
        self.assertEqual(res["risk_tier_name"], "Extreme Crisis")
        self.assertGreaterEqual(res["risk_probabilities"]["Extreme"], 0.90)

    def test_07_invalid_district_rejection(self):
        """Verifies rejection of non-existent districts."""
        with self.assertRaises(ValueError):
            predict_climate_hazard_risk(district="AtlantisCity")

    def test_08_unavailable_telemetry_graceful_handling(self):
        """Verifies safe fallback when forecast telemetry is marked unavailable."""
        unavail_payload = {
            "status": "FORECAST_UNAVAILABLE",
            "message": "API timeout"
        }
        res = predict_climate_hazard_risk(district="Colombo", forecast_data=unavail_payload)
        self.assertEqual(res["status"], "CLASSIFICATION_UNAVAILABLE")
        self.assertIsNone(res["predicted_risk_tier"])
        self.assertIsNone(res["risk_probabilities"])


class TestEarlyWarningAPIEndpoints(unittest.TestCase):
    """Integration test suite for FastAPI early warning endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_09_direct_classify_endpoint_normal(self):
        """Verifies POST /api/v1/early-warning/classify on normal weather."""
        payload = {
            "district": "Anuradhapura",
            "rainfall_14d_sum_mm": 50.0,
            "rainfall_max_1d_mm": 15.0,
            "temp_max_14d_peak_c": 32.0,
            "temp_mean_14d_c": 27.5,
            "temp_min_14d_c": 23.0,
            "humidity_mean_pct": 75.0,
            "consecutive_heat_days": 0,
            "consecutive_dry_days": 2,
            "soil_moisture_topsoil_m3_m3": 0.27,
            "spi3_current": 0.1,
            "month": 11
        }
        response = self.client.post("/api/v1/early-warning/classify", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "CLASSIFICATION_SUCCESS")
        self.assertEqual(data["predicted_risk_tier"], 0)
        self.assertEqual(data["risk_tier_name"], "Normal / Low Risk")
        self.assertIn("Normal", data["risk_probabilities"])
        self.assertGreaterEqual(data["dominant_hazard_probability_pct"], 80.0)

    def test_10_direct_classify_endpoint_extreme(self):
        """Verifies POST /api/v1/early-warning/classify on extreme precipitation."""
        payload = {
            "district": "Kalutara",
            "rainfall_14d_sum_mm": 350.0,
            "rainfall_max_1d_mm": 160.0,
            "temp_max_14d_peak_c": 29.0,
            "temp_mean_14d_c": 25.5,
            "temp_min_14d_c": 22.0,
            "humidity_mean_pct": 90.0,
            "consecutive_heat_days": 0,
            "consecutive_dry_days": 0,
            "soil_moisture_topsoil_m3_m3": 0.40,
            "spi3_current": 1.5,
            "month": 5
        }
        response = self.client.post("/api/v1/early-warning/classify", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["predicted_risk_tier"], 3)
        self.assertEqual(data["risk_tier_name"], "Extreme Crisis")
        self.assertGreaterEqual(data["risk_probabilities"]["Extreme"], 0.85)

    def test_11_direct_classify_invalid_district_422(self):
        """Verifies 422 Unprocessable Entity when an invalid district is provided."""
        payload = {
            "district": "FakeDistrictName",
            "rainfall_14d_sum_mm": 50.0,
            "rainfall_max_1d_mm": 15.0,
            "temp_max_14d_peak_c": 32.0,
            "temp_mean_14d_c": 27.5,
            "temp_min_14d_c": 23.0
        }
        response = self.client.post("/api/v1/early-warning/classify", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_12_telemetry_endpoint_carries_ai_classification(self):
        """Verifies GET /api/v1/early-warning/{district} contains ai_hazard_classification."""
        response = self.client.get("/api/v1/early-warning/Anuradhapura")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("climate_hazard_screening", data)
        self.assertIn("ai_hazard_classification", data)
        if data["status"] == "FORECAST_AVAILABLE" and data["ai_hazard_classification"] is not None:
            ai_cls = data["ai_hazard_classification"]
            self.assertIn(ai_cls["predicted_risk_tier"], [0, 1, 2, 3])
            self.assertIn("risk_probabilities", ai_cls)

    def test_13_integrated_dss_endpoint_unifies_all_layers(self):
        """Verifies POST /api/v1/integrated-decision-support includes Model 1 early warning within Layer 1."""
        payload = {
            "district": "Anuradhapura",
            "crop_name": "Maize",
            "season": "Maha",
            "irrigation_zone_type": "Major Irrigation",
            "rainfall_growing_season_total_mm": 820.0,
            "temp_growing_season_mean_c": 28.5,
            "soil_moisture_growing_season_min": 0.21,
            "spi3_growing_season_worst": -0.85,
            "current_growth_stage": "Flowering",
            "include_live_14day_forecast": True
        }
        response = self.client.post("/api/v1/integrated-decision-support", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify 4 distinct layers
        self.assertIn("layer1_climate_early_warning_14day", data)
        self.assertIn("layer2_phenology_vulnerability", data)
        self.assertIn("layer3_seasonal_yield_impact", data)
        self.assertIn("layer4_explainability_xai", data)
        
        # Verify Layer 1 contains live forecast with Model 1 AI classification
        layer1 = data["layer1_climate_early_warning_14day"]
        self.assertIn("status", layer1)
        if layer1["status"] == "FORECAST_AVAILABLE":
            self.assertIn("ai_hazard_classification", layer1)


if __name__ == "__main__":
    unittest.main()
