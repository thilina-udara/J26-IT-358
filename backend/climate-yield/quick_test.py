"""
Quick Live Verification Script for Model 1 (Climate Early Warning Classifier)
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

backend_dir = r"D:\Project\GitHubClone\J26-IT-358\backend\climate-yield"
if os.path.exists(backend_dir) and backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from pipelines.early_warning_classifier_engine import predict_climate_hazard_risk

print("=" * 75)
print("LIVE MODEL 1 INFERENCE TEST (Tuned Multi-Class XGBoost)")
print("=" * 75)

# Test 1: Normal Safe Agricultural Weather (Anuradhapura)
print("\n[TEST 1] Normal Agricultural Weather in Anuradhapura:")
normal = predict_climate_hazard_risk(
    district="Anuradhapura",
    rainfall_14d_sum_mm=50.0,
    rainfall_max_1d_mm=15.0,
    temp_max_14d_peak_c=31.0,
    temp_mean_14d_c=27.5,
    temp_min_14d_c=23.0,
    soil_moisture_topsoil_m3_m3=0.28,
    spi3_current=0.1
)
print("  Predicted Risk Tier :", normal["predicted_risk_tier"])
print("  Risk Tier Name      :", normal["risk_tier_name"])
print("  Confidence Level    :", f"{normal['dominant_hazard_probability_pct']}%")
print("  Probabilities       :", normal["risk_probabilities"])
print("  Interpretation      :", normal["hazard_interpretation"])

# Test 2: Catastrophic Flood Rainfall (Ratnapura)
print("\n" + "-" * 75)
print("\n[TEST 2] Catastrophic Flood Rainfall in Ratnapura:")
flood = predict_climate_hazard_risk(
    district="Ratnapura",
    rainfall_14d_sum_mm=450.0,
    rainfall_max_1d_mm=180.0,
    temp_max_14d_peak_c=28.0,
    temp_mean_14d_c=25.0,
    temp_min_14d_c=21.0,
    soil_moisture_topsoil_m3_m3=0.45,
    spi3_current=1.8
)
print("  Predicted Risk Tier :", flood["predicted_risk_tier"])
print("  Risk Tier Name      :", flood["risk_tier_name"])
print("  Confidence Level    :", f"{flood['dominant_hazard_probability_pct']}%")
print("  Probabilities       :", flood["risk_probabilities"])
print("  Interpretation      :", flood["hazard_interpretation"])

# Test 3: Severe Drought Crisis (Mannar)
print("\n" + "-" * 75)
print("\n[TEST 3] Severe Compound Drought Crisis in Mannar:")
drought = predict_climate_hazard_risk(
    district="Mannar",
    rainfall_14d_sum_mm=1.0,
    rainfall_max_1d_mm=0.5,
    temp_max_14d_peak_c=38.0,
    temp_mean_14d_c=33.0,
    temp_min_14d_c=28.0,
    consecutive_dry_days=14,
    consecutive_heat_days=8,
    soil_moisture_topsoil_m3_m3=0.10,
    spi3_current=-2.5
)
print("  Predicted Risk Tier :", drought["predicted_risk_tier"])
print("  Risk Tier Name      :", drought["risk_tier_name"])
print("  Confidence Level    :", f"{drought['dominant_hazard_probability_pct']}%")
print("  Probabilities       :", drought["risk_probabilities"])
print("  Interpretation      :", drought["hazard_interpretation"])
print("\n" + "=" * 75)
