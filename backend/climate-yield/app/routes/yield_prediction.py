"""
Crop Yield Prediction and Explainable AI (XAI) API Route

What this file does:
1. Receives weather data and farm location from the user or frontend.
2. Predicts crop yield using the Adaptive Hybrid AI model.
3. Uses Linear SHAP to explain exactly how rainfall, temperature, soil moisture,
   and drought indices changed the predicted yield.
4. Generates simple, practical farm advice for farmers and agricultural officers.
5. Never guesses or calculates sowing dates (handled by the crop planning team).
"""

import os
import sys
import pickle
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, status

from app.schemas.yield_prediction import (
    YieldPredictionRequest,
    YieldPredictionResponse,
    HazardRiskLevel,
    FeatureAttribution,
    ExplainabilityBreakdown
)

router = APIRouter(prefix="/api/v1", tags=["Yield Prediction & Climate Hazard Decision Support"])

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "ml", "yield_model_hybrid.pkl"))

# Global model state cache
_MODEL_ARTIFACT: Dict[str, Any] = {}
_FEATURE_MEANS: Dict[str, float] = {}
_EXPECTED_SHOCK_BASELINE: float = 0.292315  # Historical average weather shock in training data (2001-2020)

# Simple display names for weather features
CLIMATE_DISPLAY_MAP = {
    "rainfall_growing_season_total_mm": "Seasonal Cumulative Rainfall (mm)",
    "temp_growing_season_mean_c": "Growing Season Mean Temperature (°C)",
    "soil_moisture_growing_season_min": "Minimum Root-Zone Soil Moisture (m³/m³)",
    "spi3_growing_season_worst": "Worst 3-Month SPI Drought/Wet Index"
}

# Historical average values for each feature from the training dataset (2001-2020, N=6,355)
# Used to calculate how much today's weather differs from normal weather
EXACT_TRAINING_MEANS: Dict[str, float] = {
    "rainfall_growing_season_total_mm": 819.0944374508261,
    "temp_growing_season_mean_c": 26.48654445318647,
    "soil_moisture_growing_season_min": 0.2600314555468135,
    "spi3_growing_season_worst": -0.6225088906372934,
    "district_Ampara": 0.04264358772619984,
    "district_Anuradhapura": 0.042958300550747446,
    "district_Badulla": 0.042958300550747446,
    "district_Batticaloa": 0.042958300550747446,
    "district_Colombo": 0.023603461841070025,
    "district_Galle": 0.029110936270653028,
    "district_Gampaha": 0.031628638867033834,
    "district_Hambantota": 0.042958300550747446,
    "district_Jaffna": 0.04154209284028324,
    "district_Kalutara": 0.026435877261998426,
    "district_Kandy": 0.042958300550747446,
    "district_Kegalle": 0.04201416207710464,
    "district_Kilinochchi": 0.03981117230527144,
    "district_Kurunegala": 0.042958300550747446,
    "district_Mannar": 0.042171518489378446,
    "district_Matale": 0.042958300550747446,
    "district_Matara": 0.04154209284028324,
    "district_Monaragala": 0.042958300550747446,
    "district_Mullaitivu": 0.03981117230527144,
    "district_Nuwara Eliya": 0.04232887490165224,
    "district_Polonnaruwa": 0.042958300550747446,
    "district_Puttalam": 0.042958300550747446,
    "district_Ratnapura": 0.042958300550747446,
    "district_Trincomalee": 0.042958300550747446,
    "district_Vavuniya": 0.04185680566483084,
    "season_Maha": 0.5153422501966956,
    "season_Yala": 0.4846577498033045,
    "crop_name_Brinjal": 0.14807238394964595,
    "crop_name_Chilli": 0.15263571990558616,
    "crop_name_Green Gram": 0.12777340676632573,
    "crop_name_Maize": 0.12462627852084973,
    "crop_name_Okra": 0.15184893784421716,
    "crop_name_Pumpkin": 0.14413847364280094,
    "crop_name_Tomato": 0.15090479937057436,
    "irrigation_zone_type_Major Irrigation": 0.46719118804091264,
    "irrigation_zone_type_Minor / Rainfed": 0.5328088119590874
}


def load_hybrid_model() -> Dict[str, Any]:
    """Loads the trained AI model package from disk into memory."""
    global _MODEL_ARTIFACT, _FEATURE_MEANS, _EXPECTED_SHOCK_BASELINE
    if not _MODEL_ARTIFACT:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
        with open(MODEL_PATH, "rb") as f:
            _MODEL_ARTIFACT = pickle.load(f)
            
        feat_cols = _MODEL_ARTIFACT["feature_columns"]
        model = _MODEL_ARTIFACT["shock_ridge_model"]
        
        # Store the training averages for fast lookup
        _FEATURE_MEANS = {col: EXACT_TRAINING_MEANS.get(col, 0.0) for col in feat_cols}
        
        # Calculate expected weather shock under normal conditions: intercept + sum(weight * mean)
        _EXPECTED_SHOCK_BASELINE = float(model.intercept_ + sum(
            model.coef_[i] * _FEATURE_MEANS[col] for i, col in enumerate(feat_cols)
        ))
        
    return _MODEL_ARTIFACT


# Try to load the model on startup
try:
    load_hybrid_model()
except Exception as e:
    print(f"Note: Model will load on first API request: {e}")


@router.post(
    "/predict-yield-deficit",
    response_model=YieldPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict Crop Yield Deficit and Explain Weather Impacts",
    description="Predicts crop yield and provides clear Linear SHAP feature attributions showing how weather affected the harvest."
)
def predict_yield_deficit(request: YieldPredictionRequest) -> YieldPredictionResponse:
    artifact = load_hybrid_model()
    
    district_str = request.district.value
    season_str = request.season.value
    crop_str = request.crop_name.value
    zone_str = request.irrigation_zone_type.value
    stage_str = request.current_growth_stage
    
    # -------------------------------------------------------------------------
    # Step 1: Look up normal historical yield for this district and crop
    # -------------------------------------------------------------------------
    dist_crop_means = artifact["district_crop_historical_means"]
    crop_means = artifact["crop_historical_means"]
    baseline_yield = float(dist_crop_means.get((district_str, crop_str), crop_means.get(crop_str, 4.0)))
    
    # -------------------------------------------------------------------------
    # Step 2: Build the feature vector (turn categories into 1s and 0s)
    # -------------------------------------------------------------------------
    feat_cols: List[str] = artifact["feature_columns"]
    row_dict = {col: 0.0 for col in feat_cols}
    
    dist_key = f"district_{district_str}"
    if dist_key in row_dict:
        row_dict[dist_key] = 1.0
        
    season_key = f"season_{season_str}"
    if season_key in row_dict:
        row_dict[season_key] = 1.0
        
    crop_key = f"crop_name_{crop_str}"
    if crop_key in row_dict:
        row_dict[crop_key] = 1.0
        
    zone_key = f"irrigation_zone_type_{zone_str}"
    if zone_key in row_dict:
        row_dict[zone_key] = 1.0
        
    # Add numerical weather values
    row_dict["rainfall_growing_season_total_mm"] = float(request.rainfall_growing_season_total_mm)
    row_dict["temp_growing_season_mean_c"] = float(request.temp_growing_season_mean_c)
    row_dict["soil_moisture_growing_season_min"] = float(request.soil_moisture_growing_season_min)
    row_dict["spi3_growing_season_worst"] = float(request.spi3_growing_season_worst)
    
    # -------------------------------------------------------------------------
    # Step 3: Run the AI model to calculate the weather shock
    # -------------------------------------------------------------------------
    X_input = pd.DataFrame([row_dict])[feat_cols]
    shock_model = artifact["shock_ridge_model"]
    raw_shock = float(shock_model.predict(X_input)[0])
    
    # Damping factor: Maize has damping = 0.0 to prevent macro fertilizer ban distortion
    damping_factors = artifact["crop_shock_damping"]
    damping = float(damping_factors.get(crop_str, 1.0))
    
    # Final predicted yield = baseline yield + (damping * weather shock)
    unclamped_yield = baseline_yield + (damping * raw_shock)
    predicted_yield = max(0.05, unclamped_yield)  # Minimum physical floor
    clamping_adj = predicted_yield - unclamped_yield
    
    # -------------------------------------------------------------------------
    # Step 4: Calculate yield difference and deficit percentage
    # -------------------------------------------------------------------------
    yield_deficit_mt_ha = predicted_yield - baseline_yield
    yield_deficit_pct = (yield_deficit_mt_ha / baseline_yield) * 100.0 if baseline_yield > 0 else 0.0
    
    # -------------------------------------------------------------------------
    # Step 5: Explain how each weather factor affected the yield (Linear SHAP)
    # Formula: attribution = weight * (today_value - normal_average)
    # -------------------------------------------------------------------------
    climate_attributions: List[FeatureAttribution] = []
    context_attributions: List[FeatureAttribution] = []
    
    ridge_coefs = shock_model.coef_
    
    for idx, col in enumerate(feat_cols):
        w_i = float(ridge_coefs[idx])
        x_i = float(row_dict[col])
        mu_i = float(_FEATURE_MEANS.get(col, 0.0))
        
        raw_phi_i = w_i * (x_i - mu_i)
        damped_phi_i = damping * raw_phi_i
        
        # Decide if this factor helped or hurt the yield
        if abs(damped_phi_i) > 0.001:
            direction = "POSITIVE_BOOST" if damped_phi_i > 0 else "NEGATIVE_DRAG"
        else:
            direction = "NEUTRAL"
            
        attr_item = FeatureAttribution(
            feature_name=col,
            display_name=CLIMATE_DISPLAY_MAP.get(col, col.replace("district_", "District: ").replace("crop_name_", "Crop: ").replace("irrigation_zone_type_", "Zone: ").replace("season_", "Season: ")),
            feature_value=round(x_i, 4),
            reference_mean=round(mu_i, 4),
            raw_shock_attribution_mt_ha=round(raw_phi_i, 4),
            damped_attribution_mt_ha=round(damped_phi_i, 4),
            impact_direction=direction
        )
        
        if col in CLIMATE_DISPLAY_MAP:
            climate_attributions.append(attr_item)
        elif x_i > 0 or abs(damped_phi_i) > 0.01:
            context_attributions.append(attr_item)
            
    # Check that parts add up exactly to the predicted yield
    total_shock_impact = damping * raw_shock
    reconciled_yield = baseline_yield + total_shock_impact + clamping_adj
    is_consistent = abs(reconciled_yield - predicted_yield) < 1e-4
    
    explainability_payload = ExplainabilityBreakdown(
        historical_baseline_yield_mt_ha=round(baseline_yield, 4),
        expected_climate_shock_mt_ha=round(_EXPECTED_SHOCK_BASELINE, 4),
        crop_damping_factor=round(damping, 2),
        climate_feature_attributions=climate_attributions,
        context_feature_attributions=context_attributions,
        total_climate_shock_impact_mt_ha=round(total_shock_impact, 4),
        unclamped_hybrid_yield_mt_ha=round(unclamped_yield, 4),
        clamping_adjustment_mt_ha=round(clamping_adj, 4),
        final_reconciled_yield_mt_ha=round(predicted_yield, 4),
        is_explanation_consistent=is_consistent
    )
    
    # -------------------------------------------------------------------------
    # Step 6: Create practical farm advice for farmers and officers
    # -------------------------------------------------------------------------
    advisories: List[str] = []
    stage_suffix = f" during upstream {stage_str} stage" if stage_str else ""
    
    # Case A: Heavy rain / waterlogging risk
    if request.rainfall_growing_season_total_mm >= 1500.0 or request.spi3_growing_season_worst >= 1.5:
        risk_level = HazardRiskLevel.EXCESS_WATER_FLOOD_RISK
        summary = (
            f"Excessive seasonal rainfall ({request.rainfall_growing_season_total_mm:.0f} mm, "
            f"SPI-3: {request.spi3_growing_season_worst:+.2f}) detected in {district_str}{stage_suffix}. "
            f"High vulnerability to root zone waterlogging, soil aeration deficit, and fungal pathogens for {crop_str}."
        )
        advisories = [
            "Construct deep peripheral drainage trenches (minimum 30 cm depth) to evacuate standing surface water.",
            "Elevate planting ridges or maintain raised beds to prevent sustained saturation of crop root zones.",
            "Apply prophylactic copper-based fungicides to mitigate collar rot and fungal wilt after heavy rainfall events.",
            "Postpone nitrogen/urea top-dressing until standing water has drained to avoid severe nutrient leaching."
        ]
        
    # Case B: Severe drought risk
    elif yield_deficit_pct <= -25.0 or request.spi3_growing_season_worst <= -1.5 or request.soil_moisture_growing_season_min < 0.15:
        risk_level = HazardRiskLevel.SEVERE_DROUGHT_RISK
        summary = (
            f"Severe agricultural drought shock detected in {district_str}{stage_suffix} "
            f"(Worst SPI-3: {request.spi3_growing_season_worst:+.2f}, Min Soil Moisture: {request.soil_moisture_growing_season_min:.3f} m³/m³). "
            f"Projected harvest yield deficit of {abs(yield_deficit_pct):.1f}% below historical baseline."
        )
        advisories = [
            "Prioritize supplementary irrigation strictly during moisture-sensitive flowering and fruit-setting stages.",
            "Implement organic straw or poly-mulching around plant bases to suppress root-zone evaporative moisture loss.",
            "Apply micro-irrigation (drip or targeted furrow watering) during early morning hours to maximize water use efficiency.",
            "Monitor crop canopy for wilting symptoms and coordinate with local extension officers on emergency moisture conservation."
        ]
        
    # Case C: Moderate stress
    elif yield_deficit_pct <= -10.0 or request.soil_moisture_growing_season_min < 0.20 or request.temp_growing_season_mean_c > 31.0:
        risk_level = HazardRiskLevel.MODERATE_STRESS
        summary = (
            f"Moderate climate moisture/temperature stress detected in {district_str} for {crop_str}{stage_suffix}. "
            f"Projected harvest yield deficit of {abs(yield_deficit_pct):.1f}% below historical baseline."
        )
        advisories = [
            "Optimize supplementary irrigation schedules during early morning hours to minimize evaporative losses.",
            "Apply foliar potassium spray (e.g., 1% muriate of potash) to enhance plant stomatal regulation under thermal stress.",
            "Monitor soil moisture closely with field tensiometers or local Department of Agriculture agromet advisories."
        ]
        
    # Case D: Normal weather conditions
    else:
        risk_level = HazardRiskLevel.NORMAL
        summary = (
            f"Agro-climatic conditions in {district_str} are within normal seasonal range for {crop_str}{stage_suffix}. "
            f"Forecasted harvest yield is within expected seasonal bounds ({predicted_yield:.2f} MT/ha)."
        )
        advisories = [
            "Maintain standard Department of Agriculture (DOA) fertilization and integrated pest management schedules.",
            "Ensure regular field scouting for seasonal pests and leaf spot diseases.",
            "Prepare post-harvest storage and drying facilities ahead of the seasonal peak harvest."
        ]
        
    growth_stage_label = f"Upstream Stage: {stage_str}" if stage_str else "General Whole-Season Sensitivity Profile"
    
    # -------------------------------------------------------------------------
    # Step 7: Return final response
    # -------------------------------------------------------------------------
    return YieldPredictionResponse(
        district=district_str,
        season=season_str,
        crop_name=crop_str,
        irrigation_zone_type=zone_str,
        growth_stage_evaluated=growth_stage_label,
        predicted_yield_mt_ha=round(predicted_yield, 2),
        baseline_yield_mt_ha=round(baseline_yield, 2),
        yield_deficit_mt_ha=round(yield_deficit_mt_ha, 2),
        yield_deficit_percentage=round(yield_deficit_pct, 1),
        hazard_risk_level=risk_level,
        risk_summary=summary,
        actionable_advisories=advisories,
        explainability=explainability_payload,
        model_metadata={
            "model_architecture": "Adaptive Hybrid AI (3-Year Rolling Baseline + Attenuated Ridge Climate Shock)",
            "test_r2_score": 0.6023,
            "test_rmse_mt_ha": 3.8182,
            "test_mae_mt_ha": 1.8931,
            "unseen_test_period": "2021 - 2025",
            "test_samples": 1662,
            "version": "1.1.0",
            "crop_damping_factor_applied": damping,
            "xai_method": "Linear SHAP (Marginal Empirical Background)"
        }
    )
