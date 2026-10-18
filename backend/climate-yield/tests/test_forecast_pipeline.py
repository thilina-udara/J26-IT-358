"""
Tests for Weather Forecast and Screening Pipeline

What this test file checks:
1. Rejection of invalid district names.
2. Handling of network timeouts and server errors (safely returns FORECAST_UNAVAILABLE).
3. Rejection of missing weather variables, null values, or physically impossible numbers.
4. Ensuring high rainfall is labeled as a weather watch, NOT a confirmed river flood.
5. Live connection check to the weather API for 4 Sri Lankan districts.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock
import requests

# Add backend directory to path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pipelines.fetch_forward_climate_forecast import (
    fetch_forward_climate_forecast,
    validate_api_response,
    SRI_LANKA_DISTRICT_REPRESENTATIVE_COORDINATES,
    REQUIRED_DAILY_VARIABLES
)


class TestForwardClimateForecastPipeline(unittest.TestCase):
    """Rigorous test suite for API failure safety, data validation, and hazard screening."""

    def setUp(self):
        self.mock_daily_valid = {
            "time": [f"2026-10-{18+i:02d}" for i in range(14)],
            "precipitation_sum": [5.0] * 14,
            "temperature_2m_max": [31.0] * 14,
            "temperature_2m_min": [23.0] * 14,
            "temperature_2m_mean": [26.5] * 14,
            "soil_moisture_0_to_7cm_mean": [0.25] * 14,
            "soil_moisture_7_to_28cm_mean": [0.28] * 14
        }
        self.mock_valid_response = {
            "generationtime_ms": 1.25,
            "daily": self.mock_daily_valid
        }

    # 1. API Failure & Network Safety Tests
    def test_api_network_failure_handling(self):
        """Simulates network timeout / connection abort: MUST return FORECAST_UNAVAILABLE with zero live alerts."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.ConnectTimeout("Connection timed out after 10s")

        res = fetch_forward_climate_forecast("Anuradhapura", forecast_days=14, session=mock_session)
        
        self.assertEqual(res["status"], "FORECAST_UNAVAILABLE")
        self.assertFalse(res["metadata"]["telemetry_health"]["is_live_telemetry"])
        self.assertIn("ConnectTimeout", res["metadata"]["telemetry_health"]["validation_error"])
        
        hazard = res["climate_hazard_screening"]
        self.assertEqual(hazard["primary_hazard_classification"], "FORECAST_UNAVAILABLE")
        self.assertIsNone(hazard["screening_metrics"])
        self.assertEqual(res["daily_forecast_series"], [])
        self.assertTrue(any("telemetry is currently unavailable" in a for a in hazard["provisional_screening_alerts"]))

    def test_http_500_error_handling(self):
        """Simulates HTTP 500 internal server error from provider."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error in upstream provider"
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        res = fetch_forward_climate_forecast("Colombo", forecast_days=14, session=mock_session)
        self.assertEqual(res["status"], "FORECAST_UNAVAILABLE")
        self.assertIn("HTTP Error 500", res["metadata"]["telemetry_health"]["validation_error"])
        self.assertEqual(res["climate_hazard_screening"]["primary_hazard_classification"], "FORECAST_UNAVAILABLE")

    # 2. Data Validation & Corruption Tests
    def test_missing_daily_object(self):
        """Validates error detection when 'daily' is missing from JSON."""
        bad_json = {"error": True, "reason": "Quota Exceeded"}
        is_valid, err = validate_api_response(bad_json, 14)
        self.assertFalse(is_valid)
        self.assertIn("Missing 'daily' object", err)

    def test_missing_required_variable(self):
        """Validates detection when a critical variable (e.g., precipitation_sum) is missing."""
        corrupted = dict(self.mock_daily_valid)
        del corrupted["precipitation_sum"]
        is_valid, err = validate_api_response({"daily": corrupted}, 14)
        self.assertFalse(is_valid)
        self.assertIn("Missing required variable 'precipitation_sum'", err)

    def test_mismatched_array_length(self):
        """Validates detection when array length does not match forecast horizon."""
        corrupted = dict(self.mock_daily_valid)
        corrupted["temperature_2m_max"] = [30.0] * 10  # Only 10 days instead of 14
        is_valid, err = validate_api_response({"daily": corrupted}, 14)
        self.assertFalse(is_valid)
        self.assertIn("does not match expected days", err)

    def test_null_value_injection_in_telemetry(self):
        """Validates detection when provider returns None/null within numerical arrays."""
        corrupted = dict(self.mock_daily_valid)
        corrupted["soil_moisture_0_to_7cm_mean"] = [0.25] * 7 + [None] + [0.25] * 6
        is_valid, err = validate_api_response({"daily": corrupted}, 14)
        self.assertFalse(is_valid)
        self.assertIn("Null value encountered", err)

    def test_unphysical_bounds_detection(self):
        """Validates rejection of unphysical values (e.g., negative precipitation or extreme temp)."""
        corrupted = dict(self.mock_daily_valid)
        corrupted["precipitation_sum"] = [-10.0] + [5.0] * 13
        is_valid, err = validate_api_response({"daily": corrupted}, 14)
        self.assertFalse(is_valid)
        self.assertIn("Precipitation values outside plausible physical bounds", err)

    # 3. Hazard Interpretation & Screening Logic Tests
    def test_no_unwarranted_favorable_label(self):
        """Ensures that normal weather is NOT labeled 'FAVORABLE_CLIMATE', but 'NO_HAZARD_THRESHOLD_BREACHED'."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.mock_valid_response
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        res = fetch_forward_climate_forecast("Kurunegala", forecast_days=14, session=mock_session)
        self.assertEqual(res["status"], "FORECAST_AVAILABLE")
        hazard = res["climate_hazard_screening"]
        self.assertEqual(hazard["primary_hazard_classification"], "NO_HAZARD_THRESHOLD_BREACHED")
        self.assertNotIn("FAVORABLE_CLIMATE", hazard["primary_hazard_classification"])

    def test_precipitation_watch_is_not_flood_prediction(self):
        """Ensures high rainfall is labeled HIGH_PRECIPITATION_WATCH with explicit non-flood caveat."""
        high_rain_daily = dict(self.mock_daily_valid)
        high_rain_daily["precipitation_sum"] = [15.0] * 14  # 210 mm total
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"daily": high_rain_daily}
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        res = fetch_forward_climate_forecast("Ratnapura", forecast_days=14, session=mock_session)
        hazard = res["climate_hazard_screening"]
        self.assertEqual(hazard["primary_hazard_classification"], "HIGH_PRECIPITATION_WATCH")
        alert = hazard["provisional_screening_alerts"][0]
        self.assertIn("HIGH_PRECIPITATION_WATCH", hazard["primary_hazard_classification"])
        self.assertIn("does not constitute a confirmed flood prediction", alert)

    # 4. Spatial Location & Coordinates Integrity
    def test_representative_station_metadata(self):
        """Verifies that representative station/town metadata and spatial representation caveats are included."""
        loc = SRI_LANKA_DISTRICT_REPRESENTATIVE_COORDINATES["Anuradhapura"]
        self.assertEqual(loc["location_name"], "Anuradhapura Met Station")
        self.assertAlmostEqual(loc["lat"], 8.3114, places=3)
        self.assertAlmostEqual(loc["lon"], 80.4037, places=3)

    def test_invalid_district_rejection(self):
        """Verifies that non-existent districts raise clear ValueError."""
        with self.assertRaises(ValueError) as ctx:
            fetch_forward_climate_forecast("UnknownDistrictXYZ", forecast_days=14)
        self.assertIn("Invalid district", str(ctx.exception))


class TestLiveApiIntegration(unittest.TestCase):
    """Live API integration test across representative climatic zones."""

    def test_live_forecast_retrieval(self):
        """Executes live network check for 4 districts representing Dry, Intermediate, and Wet zones."""
        test_districts = ["Anuradhapura", "Badulla", "Colombo", "Nuwara Eliya"]
        for d in test_districts:
            with self.subTest(district=d):
                res = fetch_forward_climate_forecast(d, forecast_days=14)
                self.assertIn(res["status"], ["FORECAST_AVAILABLE", "FORECAST_UNAVAILABLE"])
                if res["status"] == "FORECAST_AVAILABLE":
                    meta = res["metadata"]
                    self.assertTrue(meta["telemetry_health"]["is_live_telemetry"])
                    self.assertEqual(meta["valid_time_window"]["horizon_days"], 14)
                    self.assertEqual(len(res["daily_forecast_series"]), 14)
                    metrics = res["climate_hazard_screening"]["screening_metrics"]
                    self.assertGreaterEqual(metrics["total_rainfall_mm"], 0.0)
                    self.assertGreaterEqual(metrics["max_temperature_c"], 5.0)
                    self.assertLessEqual(metrics["max_temperature_c"], 45.0)


if __name__ == "__main__":
    unittest.main()
