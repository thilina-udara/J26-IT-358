"""
Candidate Model 1A v3: 1-to-7 Days Ahead Flood Early Warning Inference Engine
Component 04: AI-Powered Climate Early Warning DSS
Project: J26-IT-358 (Climate-Yield DSS)

Model Provenance & Verification:
- Certified Strictly Leakage-Free (Stage G & Stage G.1 Independent Audit).
- Preprocessing climatology derived strictly from 2000-2014 training records.
- Platt calibrated on 2018-2020 validation records.
- Verified on 2021-2025 locked test period: 72.99% DMC episode detection rate with 5-7 days actionable lead time.
- ROC-AUC: 0.8151 | PR-AUC: 0.1363 | Brier Score: 0.03722
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_ARTIFACT_PATHS = [
    os.path.abspath(os.path.join(CURRENT_DIR, "..", "ml", "candidate_v3_flood_early_warning_model_1_to_7d.pkl")),
    os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "climate_research_system", "ml", "candidate_v3_flood_early_warning_model_1_to_7d.pkl")),
    os.path.abspath(os.path.join("d:", os.sep, "01_research", "climate_research_system", "ml", "candidate_v3_flood_early_warning_model_1_to_7d.pkl")),
    os.path.abspath(os.path.join("D:", os.sep, "Project", "GitHubClone", "J26-IT-358", "backend", "climate-yield", "ml", "candidate_v3_flood_early_warning_model_1_to_7d.pkl"))
]

_MODEL_V3_ARTIFACT: Optional[Dict[str, Any]] = None

OFFICIAL_DISTRICTS = [
    "Ampara", "Anuradhapura", "Badulla", "Batticaloa", "Colombo", "Galle", "Gampaha",
    "Hambantota", "Jaffna", "Kalutara", "Kandy", "Kegalle", "Kilinochchi", "Kurunegala",
    "Mannar", "Matale", "Matara", "Monaragala", "Mullaitivu", "Nuwara Eliya",
    "Polonnaruwa", "Puttalam", "Ratnapura", "Trincomalee", "Vavuniya"
]


def load_flood_model_v3() -> Dict[str, Any]:
    """Loads and caches Candidate Model 1A v3 artifact."""
    global _MODEL_V3_ARTIFACT
    if _MODEL_V3_ARTIFACT is not None:
        return _MODEL_V3_ARTIFACT

    artifact_path = None
    for p in POSSIBLE_ARTIFACT_PATHS:
        if os.path.exists(p):
            artifact_path = p
            break

    if artifact_path is None:
        raise FileNotFoundError(
            f"Candidate v3 flood model artifact not found. Checked: {POSSIBLE_ARTIFACT_PATHS}"
        )

    with open(artifact_path, "rb") as f:
        _MODEL_V3_ARTIFACT = pickle.load(f)

    return _MODEL_V3_ARTIFACT


def predict_flood_early_warning_v3(
    district: str,
    rainfall_1d_mm: float,
    rainfall_3d_sum_mm: float,
    rainfall_7d_sum_mm: float,
    rainfall_14d_sum_mm: float,
    antecedent_precip_index: float,
    upstream_rainfall_3d_mm: float = 0.0,
    rainfall_intensity_ratio: Optional[float] = None,
    temp_mean_14d_c: float = 27.0,
    temp_max_14d_peak_c: float = 31.0,
    humidity_mean_14d_pct: float = 75.0,
    soil_moisture_topsoil_m3_m3: float = 0.30
) -> Dict[str, Any]:
    """
    Executes inference using Candidate Model 1A v3.

    Operational Alerting Tiers (Clean Validation-Derived):
    - Normal  (Prob < 0.110): Routine conditions.
    - Advisory (0.110 <= Prob < 0.160): High-detection advance warning (73% episode capture, 5-7d lead time).
    - Warning  (Prob >= 0.160): High-confidence emergency response (cuts false alarms by 36.6%).
    """
    if district not in OFFICIAL_DISTRICTS:
        raise ValueError(f"Invalid district '{district}'. Must be one of: {sorted(OFFICIAL_DISTRICTS)}")

    art = load_flood_model_v3()
    base_model = art["base_model"]
    calibrator = art["calibrator"]
    features = art["features"]
    climatology = art["training_climatology_dist_mean_3d"]
    thresh_advisory = float(art["thresholds"]["advisory"])
    thresh_warning = float(art["thresholds"]["warning"])

    if rainfall_intensity_ratio is None:
        rainfall_intensity_ratio = float(rainfall_1d_mm / (rainfall_14d_sum_mm / 14.0 + 1e-4))

    # Compute training-derived relative rainfall
    dist_baseline_3d = float(climatology.get(district, 13.0))
    district_relative_rain_3d = float(rainfall_3d_sum_mm / (1.0 + dist_baseline_3d))

    # Interaction surge features
    flash_flood_shock_index = float(rainfall_1d_mm / (1.0 + antecedent_precip_index))
    compound_saturation_surge = float((rainfall_1d_mm * antecedent_precip_index) / 100.0)
    upstream_catchment_surge = float((upstream_rainfall_3d_mm * antecedent_precip_index) / 100.0)

    # Build 40-feature vector
    row_dict = {col: 0.0 for col in features}
    row_dict["rainfall_1d_mm"] = float(rainfall_1d_mm)
    row_dict["rainfall_3d_sum_mm"] = float(rainfall_3d_sum_mm)
    row_dict["rainfall_7d_sum_mm"] = float(rainfall_7d_sum_mm)
    row_dict["rainfall_14d_sum_mm"] = float(rainfall_14d_sum_mm)
    row_dict["antecedent_precip_index"] = float(antecedent_precip_index)
    row_dict["rainfall_intensity_ratio"] = float(rainfall_intensity_ratio)
    row_dict["district_relative_rain_3d"] = district_relative_rain_3d
    row_dict["flash_flood_shock_index"] = flash_flood_shock_index
    row_dict["compound_saturation_surge"] = compound_saturation_surge
    row_dict["upstream_rainfall_3d_mm"] = float(upstream_rainfall_3d_mm)
    row_dict["upstream_catchment_surge"] = upstream_catchment_surge
    row_dict["temp_mean_14d_c"] = float(temp_mean_14d_c)
    row_dict["temp_max_14d_peak_c"] = float(temp_max_14d_peak_c)
    row_dict["humidity_mean_14d_pct"] = float(humidity_mean_14d_pct)
    row_dict["soil_moisture_topsoil_m3_m3"] = float(soil_moisture_topsoil_m3_m3)

    dist_col = f"dist_{district}"
    if dist_col in row_dict:
        row_dict[dist_col] = 1.0

    X = pd.DataFrame([row_dict])[features]

    # Predict uncalibrated probability then Platt calibrated probability
    uncal_prob = float(base_model.predict_proba(X)[0, 1])
    cal_prob = float(calibrator.predict_proba(np.array([[uncal_prob]]))[0, 1])

    # Determine operational tier
    if cal_prob >= thresh_warning:
        alert_tier = "TIER_2_WARNING"
        alert_label = "Flood Warning (High Confidence)"
        alert_color = "RED"
        lead_time = "Advance Warning Active (Expect peak impacts within 1 to 5 days)"
        recommendation = "High risk of inundation. Deploy emergency response, secure low-lying crops and livestock."
    elif cal_prob >= thresh_advisory:
        alert_tier = "TIER_1_ADVISORY"
        alert_label = "Flood Advisory / Watch"
        alert_color = "AMBER"
        lead_time = "Early Warning Active (5 to 7 days advance notice)"
        recommendation = "Elevated catchment saturation and heavy rainfall surge. Prepare early harvesting and drainage."
    else:
        alert_tier = "TIER_0_NORMAL"
        alert_label = "Normal / Low Risk"
        alert_color = "GREEN"
        lead_time = "No active flood hazard expected within 1 to 7 days."
        recommendation = "Safe hydrological conditions. Routine agricultural water management."

    return {
        "district": district,
        "calibrated_flood_probability": round(cal_prob, 4),
        "calibrated_flood_probability_pct": round(cal_prob * 100, 2),
        "uncalibrated_model_score": round(uncal_prob, 4),
        "alert_tier": alert_tier,
        "alert_label": alert_label,
        "alert_color": alert_color,
        "actionable_lead_time": lead_time,
        "operational_recommendation": recommendation,
        "thresholds": {
            "advisory": thresh_advisory,
            "warning": thresh_warning
        },
        "hydrometeorological_factors": {
            "rainfall_3d_sum_mm": round(rainfall_3d_sum_mm, 2),
            "district_climatology_baseline_mm": round(dist_baseline_3d, 2),
            "surge_ratio": round(district_relative_rain_3d, 2),
            "antecedent_saturation_index": round(antecedent_precip_index, 2),
            "soil_moisture": round(soil_moisture_topsoil_m3_m3, 3)
        },
        "model_performance_metadata": {
            "model_version": "Candidate Model 1A v3 (Strictly Leakage-Free)",
            "historical_episode_detection_rate": "72.99%",
            "mean_actionable_lead_time": "5.49 days (Median: 7 days)",
            "roc_auc": 0.8151,
            "pr_auc": 0.1363,
            "brier_score": 0.03722
        }
    }
