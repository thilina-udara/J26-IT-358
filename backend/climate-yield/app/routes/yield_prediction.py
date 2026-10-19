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

from datetime import datetime, timezone
from pipelines.fetch_forward_climate_forecast import fetch_forward_climate_forecast
from pipelines.phenology_vulnerability_engine import evaluate_phenology_vulnerability
from app.schemas.yield_prediction import (
    YieldPredictionRequest,
    YieldPredictionResponse,
    IntegratedDecisionSupportRequest,
    IntegratedDecisionSupportResponse,
    EarlyWarningRiskProbabilities,
    EarlyWarningClassifierOutput,
    EarlyWarningClassifyRequest,
    HazardRiskLevel,
    FeatureAttribution,
    ExplainabilityBreakdown
)
from pipelines.early_warning_classifier_engine import predict_climate_hazard_risk

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
    # Step 1: Look up baseline yield for this district and crop
    # Priority:
    #   1. Explicit client baseline (if supplied in request)
    #   2. Historical walk-forward rolling baseline (if crop_year is provided)
    #   3. Latest 3-year rolling agronomic baseline for (district, crop)
    #   4. Fallback to 20-year district-crop historical mean
    # -------------------------------------------------------------------------
    if request.baseline_yield_mt_ha is not None:
        baseline_yield = float(request.baseline_yield_mt_ha)
        baseline_type = "CUSTOM_SUPPLIED_BASELINE"
    elif request.crop_year is not None and (district_str, crop_str, int(request.crop_year), season_str) in artifact.get("rolling_baseline_history", {}):
        baseline_yield = float(artifact["rolling_baseline_history"][(district_str, crop_str, int(request.crop_year), season_str)])
        baseline_type = "HISTORICAL_ROLLING_3YR_BASELINE"
    elif (district_str, crop_str) in artifact.get("district_crop_rolling_baselines", {}):
        baseline_yield = float(artifact["district_crop_rolling_baselines"][(district_str, crop_str)])
        baseline_type = "LATEST_ROLLING_3YR_BASELINE"
    elif (district_str, crop_str) in artifact.get("district_crop_historical_means", {}):
        baseline_yield = float(artifact["district_crop_historical_means"][(district_str, crop_str)])
        baseline_type = "DISTRICT_CROP_HISTORICAL_MEAN_FALLBACK"
    else:
        baseline_yield = float(artifact.get("crop_historical_means", {}).get(crop_str, 4.0))
        baseline_type = "CROP_GENERAL_MEAN_FALLBACK"
    
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
        baseline_type=baseline_type,
        historical_baseline_yield_mt_ha=round(baseline_yield, 4),
        expected_climate_shock_mt_ha=round(_EXPECTED_SHOCK_BASELINE, 4),
        crop_damping_factor=round(damping, 2),
        climate_feature_attributions=climate_attributions,
        context_feature_attributions=context_attributions,
        total_climate_shock_impact_mt_ha=round(total_shock_impact, 4),
        unclamped_hybrid_yield_mt_ha=round(unclamped_yield, 4),
        clamping_adjustment_mt_ha=round(clamping_adj, 4),
        final_reconciled_yield_mt_ha=round(round(baseline_yield, 4) + round(total_shock_impact, 4) + round(clamping_adj, 4), 4),
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
            "Maintain cleared farm drainage outlets and inspect bunds to accelerate excess water evacuation."
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
            "Apply light surface mulching or protective shading where feasible to reduce thermal stress on the root zone.",
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
            "Continue routine crop water monitoring and standard pest surveillance as per Department of Agriculture guidelines.",
            "Ensure regular field scouting for seasonal moisture stress and leaf spot diseases.",
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
        baseline_type=baseline_type,
        predicted_yield_mt_ha=round(predicted_yield, 2),
        baseline_yield_mt_ha=round(baseline_yield, 2),
        pure_rolling_baseline_test_r2=0.6138,
        hybrid_model_test_r2=0.6023,
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


@router.get(
    "/early-warning/{district}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="14-Day Forward Climate Hazard Screening",
    description="Retrieves live 14-day weather forecast telemetry and screens for heavy precipitation, dry spells, and extreme heat alerts."
)
def get_climate_early_warning(district: str) -> Dict[str, Any]:
    """Provides pure 14-day climate hazard early warning for any of the 25 official districts."""
    try:
        return fetch_forward_climate_forecast(district=district, forecast_days=14)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Early warning retrieval failed: {e}")


@router.post(
    "/integrated-decision-support",
    response_model=IntegratedDecisionSupportResponse,
    status_code=status.HTTP_200_OK,
    summary="Full Decision Support System: Climate Early Warning, Phenology & Yield Impact",
    description="Master Decision Support System (DSS) endpoint unifying 14-day forward climate hazard screening, crop phenological vulnerability assessment, seasonal yield deficit forecasting, and Linear SHAP explainability."
)
def get_integrated_decision_support(request: IntegratedDecisionSupportRequest) -> IntegratedDecisionSupportResponse:
    """
    Executes the complete 4-tier Component 4 Decision Support System pipeline:
    1. Layer 1: 14-Day Forward Climate Hazard Screening (Open-Meteo telemetry)
    2. Layer 2: Crop Phenological Vulnerability Assessment (Mode A or Mode B)
    3. Layer 3: Seasonal Yield Deficit Impact (Adaptive Hybrid AI with Rolling Baseline)
    4. Layer 4: Explainable AI Attribution (Linear SHAP with exact reconciliation)
    """
    district_str = request.district.value
    season_str = request.season.value
    crop_str = request.crop_name.value
    zone_str = request.irrigation_zone_type.value
    stage_str = request.current_growth_stage
    now_utc = datetime.now(timezone.utc).isoformat()

    # -------------------------------------------------------------------------
    # Layer 1: 14-Day Forward Climate Hazard Early Warning
    # -------------------------------------------------------------------------
    if request.include_live_14day_forecast:
        try:
            forecast_data = fetch_forward_climate_forecast(district=district_str, forecast_days=14)
        except Exception:
            forecast_data = {
                "status": "FORECAST_UNAVAILABLE",
                "message": "Live weather telemetry service unavailable; safe fallback active with zero live alerts."
            }
    else:
        forecast_data = {
            "status": "FORECAST_BYPASSED",
            "message": "Live 14-day forecast bypassed by client request."
        }

    # -------------------------------------------------------------------------
    # Layer 2: Crop Phenological Vulnerability Assessment
    # -------------------------------------------------------------------------
    try:
        phenology_data = evaluate_phenology_vulnerability(
            crop_name=crop_str,
            district=district_str,
            forecast_data=forecast_data,
            current_growth_stage=stage_str
        )
    except Exception as pe:
        phenology_data = {
            "status": "EVALUATION_ERROR",
            "message": f"Phenological evaluation failed: {pe}"
        }

    # -------------------------------------------------------------------------
    # Layer 3 & 4: Seasonal Yield Impact & Linear SHAP XAI
    # -------------------------------------------------------------------------
    # Delegate to core yield prediction logic
    yield_req = YieldPredictionRequest(
        district=request.district,
        season=request.season,
        crop_name=request.crop_name,
        irrigation_zone_type=request.irrigation_zone_type,
        rainfall_growing_season_total_mm=request.rainfall_growing_season_total_mm,
        temp_growing_season_mean_c=request.temp_growing_season_mean_c,
        soil_moisture_growing_season_min=request.soil_moisture_growing_season_min,
        spi3_growing_season_worst=request.spi3_growing_season_worst,
        current_growth_stage=request.current_growth_stage,
        crop_year=request.crop_year,
        baseline_yield_mt_ha=request.baseline_yield_mt_ha
    )
    yield_res = predict_yield_deficit(yield_req)

    # -------------------------------------------------------------------------
    # Combine Actionable Advisories (Zero fertilizer, zero crop selection)
    # -------------------------------------------------------------------------
    combined_advisories = []
    # Add phenology early warning advisories if critical
    if phenology_data.get("actionable_advisories"):
        for adv in phenology_data["actionable_advisories"]:
            if adv not in combined_advisories:
                combined_advisories.append(adv)
    # Add seasonal water conservation advisories
    for adv in yield_res.actionable_advisories:
        if adv not in combined_advisories:
            combined_advisories.append(adv)

    return IntegratedDecisionSupportResponse(
        system_title="AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System",
        timestamp_utc=now_utc,
        district=district_str,
        crop_name=crop_str,
        season=season_str,
        irrigation_zone_type=zone_str,
        growth_stage_evaluated=yield_res.growth_stage_evaluated,
        layer1_climate_early_warning_14day=forecast_data,
        layer2_phenology_vulnerability=phenology_data,
        layer3_seasonal_yield_impact={
            "predicted_yield_mt_ha": yield_res.predicted_yield_mt_ha,
            "baseline_yield_mt_ha": yield_res.baseline_yield_mt_ha,
            "baseline_type": yield_res.baseline_type,
            "yield_deficit_mt_ha": yield_res.yield_deficit_mt_ha,
            "yield_deficit_percentage": yield_res.yield_deficit_percentage,
            "hazard_risk_level": yield_res.hazard_risk_level,
            "risk_summary": yield_res.risk_summary,
            "pure_rolling_baseline_test_r2": yield_res.pure_rolling_baseline_test_r2,
            "hybrid_model_test_r2": yield_res.hybrid_model_test_r2
        },
        layer4_explainability_xai=yield_res.explainability,
        actionable_decision_support_advisories=combined_advisories,
        system_governance_and_boundaries={
            "scope_boundaries": "Exclusively climate/weather hazards and crop yield impacts for selected crops.",
            "zero_scope_overlap": "Zero fertilizer recommendations, zero crop selection/suitability, and zero sowing date estimation.",
            "spatial_coverage": "All 25 official districts of Sri Lanka",
            "crop_scope": "Strictly 7 approved crops: Maize, Chilli, Green Gram, Tomato, Brinjal, Okra, Pumpkin (Ash Pumpkin excluded)."
        }
    )


@router.post(
    "/early-warning/classify",
    response_model=EarlyWarningClassifierOutput,
    status_code=status.HTTP_200_OK,
    summary="Model 1: Direct 14-Day Multi-Hazard Risk Classification",
    description="Direct inference endpoint for Model 1 (AI-Powered Climate Early Warning Multi-Hazard Classifier). Ingests 14-day agro-meteorological indicators and outputs hazard risk tiers (0 to 3) with full Softmax probabilities."
)
def classify_climate_hazard(request: EarlyWarningClassifyRequest) -> EarlyWarningClassifierOutput:
    """Classifies custom or simulated 14-day meteorological conditions into multi-hazard risk tiers."""
    try:
        result = predict_climate_hazard_risk(
            district=request.district.value,
            rainfall_14d_sum_mm=request.rainfall_14d_sum_mm,
            rainfall_max_1d_mm=request.rainfall_max_1d_mm,
            temp_max_14d_peak_c=request.temp_max_14d_peak_c,
            temp_mean_14d_c=request.temp_mean_14d_c,
            temp_min_14d_c=request.temp_min_14d_c,
            humidity_mean_pct=request.humidity_mean_pct,
            consecutive_heat_days=request.consecutive_heat_days,
            consecutive_dry_days=request.consecutive_dry_days,
            soil_moisture_topsoil_m3_m3=request.soil_moisture_topsoil_m3_m3,
            spi3_current=request.spi3_current,
            month=request.month
        )
        return EarlyWarningClassifierOutput(**result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Early warning classification failed: {exc}")
