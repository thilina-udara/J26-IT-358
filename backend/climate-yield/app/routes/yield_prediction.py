"""
Crop Yield Prediction & Climate Early Warning Router
Component 4: AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status

from app.schemas.yield_prediction import (
    YieldPredictionRequest,
    YieldPredictionResponse,
    HazardRiskLevel,
)

router = APIRouter(prefix="/api/v1", tags=["Yield Prediction & Climate Early Warning"])

# Path to the pre-trained hybrid model artifact
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "ml", "yield_model_hybrid.pkl"))

# Global model state cache
_MODEL_ARTIFACT: Dict[str, Any] = {}


def load_hybrid_model():
    """Load and cache the trained hybrid yield model into memory on startup."""
    global _MODEL_ARTIFACT
    if not _MODEL_ARTIFACT:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model artifact not found at: {MODEL_PATH}")
        with open(MODEL_PATH, "rb") as f:
            _MODEL_ARTIFACT = pickle.load(f)
    return _MODEL_ARTIFACT


# Load artifact immediately when module is imported
try:
    load_hybrid_model()
except Exception as e:
    # Graceful warning if running in lightweight test mode
    print(f"Warning: Hybrid model artifact not loaded immediately: {e}")


@router.post(
    "/predict-yield-deficit",
    response_model=YieldPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict Seasonal Crop Yield Deficit & Climate Hazard Risk",
    description=(
        "Evaluates pre-harvest crop yield impact and multi-hazard climate risk "
        "for 7 non-paddy crops across Sri Lanka's 25 districts using the Adaptive Hybrid AI model (R² = 0.6023)."
    )
)
def predict_yield_deficit(request: YieldPredictionRequest) -> YieldPredictionResponse:
    artifact = load_hybrid_model()
    
    district_str = request.district.value
    season_str = request.season.value
    crop_str = request.crop_name.value
    zone_str = request.irrigation_zone_type.value
    
    # 1. Retrieve Historical Baseline Yield for (District, Crop)
    dist_crop_means = artifact["district_crop_historical_means"]
    crop_means = artifact["crop_historical_means"]
    baseline_yield = dist_crop_means.get((district_str, crop_str), crop_means.get(crop_str, 4.0))
    
    # 2. Construct One-Hot Feature Vector
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
        
    row_dict["rainfall_growing_season_total_mm"] = float(request.rainfall_growing_season_total_mm)
    row_dict["temp_growing_season_mean_c"] = float(request.temp_growing_season_mean_c)
    row_dict["soil_moisture_growing_season_min"] = float(request.soil_moisture_growing_season_min)
    row_dict["spi3_growing_season_worst"] = float(request.spi3_growing_season_worst)
    
    # 3. Model Inference (Climate Shock + Damping)
    X_input = pd.DataFrame([row_dict])[feat_cols]
    shock_model = artifact["shock_ridge_model"]
    raw_shock = float(shock_model.predict(X_input)[0])
    
    damping_factors = artifact["crop_shock_damping"]
    damping = float(damping_factors.get(crop_str, 1.0))
    
    predicted_yield = max(0.05, float(baseline_yield + (damping * raw_shock)))
    
    # 4. Deficit Metrics
    yield_deficit_mt_ha = predicted_yield - baseline_yield
    yield_deficit_pct = (yield_deficit_mt_ha / baseline_yield) * 100.0 if baseline_yield > 0 else 0.0
    
    # 5. Multi-Hazard Classification & Decision Support Engine
    advisories: List[str] = []
    
    # Check for Excessive Monsoon Rain / Flood Hazard First
    if request.rainfall_growing_season_total_mm >= 1500.0 or request.spi3_growing_season_worst >= 1.5:
        risk_level = HazardRiskLevel.EXCESS_WATER_FLOOD_RISK
        summary = (
            f"Excessive seasonal monsoon deluge ({request.rainfall_growing_season_total_mm:.0f} mm, "
            f"SPI-3: {request.spi3_growing_season_worst:+.2f}) detected in {district_str}. "
            f"Severe risk of field inundation, root asphyxiation, and fungal rot for {crop_str}."
        )
        advisories = [
            "Construct deep peripheral drainage trenches (minimum 30 cm depth) to evacuate standing water.",
            "Elevate planting beds/ridges for upland crops to prevent root zone saturation.",
            "Apply prophylactic copper-based fungicides to prevent post-flood collar rot and bacterial wilt.",
            "Postpone nitrogen/urea fertilizer top-dressing until excess surface water has drained to avoid nutrient leaching."
        ]
        
    # Check for Severe Drought Hazard
    elif yield_deficit_pct <= -25.0 or request.spi3_growing_season_worst <= -1.5 or request.soil_moisture_growing_season_min < 0.15:
        risk_level = HazardRiskLevel.SEVERE_DROUGHT_RISK
        summary = (
            f"Severe agricultural drought shock detected in {district_str} "
            f"(Worst SPI-3: {request.spi3_growing_season_worst:+.2f}, Soil Moisture: {request.soil_moisture_growing_season_min:.3f} m³/m³). "
            f"Projected harvest yield deficit of {abs(yield_deficit_pct):.1f}% below historical baseline."
        )
        advisories = [
            "Prioritize critical irrigation windows during flowering and pod/fruit setting stages to prevent flower drop.",
            "Implement organic straw or poly-mulching around crop root zones to suppress soil moisture evaporation.",
            "If sowing has not commenced, adopt certified short-duration drought-tolerant varieties (e.g. DOA Maize 'Bhadra' or Green Gram 'MI-6').",
            "Consider partial-extent Bethma rotational cultivation if irrigation reservoir storage is below 30%."
        ]
        
    # Check for Moderate Moisture/Heat Stress
    elif yield_deficit_pct <= -10.0 or request.soil_moisture_growing_season_min < 0.20 or request.temp_growing_season_mean_c > 31.0:
        risk_level = HazardRiskLevel.MODERATE_STRESS
        summary = (
            f"Moderate climate moisture/temperature stress detected in {district_str} for {crop_str}. "
            f"Projected harvest yield deficit of {abs(yield_deficit_pct):.1f}% below historical baseline."
        )
        advisories = [
            "Optimize supplementary irrigation schedules during early morning hours to minimize evaporative losses.",
            "Apply foliar potassium spray (e.g. 1% muriate of potash) to enhance plant stomatal regulation under heat stress.",
            "Monitor soil moisture closely with field tensiometers or local Department of Agriculture agromet advisories."
        ]
        
    # Favorable / Normal Conditions
    else:
        risk_level = HazardRiskLevel.NORMAL
        summary = (
            f"Agro-climatic conditions in {district_str} are favorable for {crop_str} cultivation. "
            f"Forecasted harvest yield is within normal seasonal bounds ({predicted_yield:.2f} MT/ha)."
        )
        advisories = [
            "Maintain standard Department of Agriculture (DOA) fertilization and integrated pest management schedules.",
            "Ensure regular field scouting for seasonal fall armyworm or pod borer pests.",
            "Prepare post-harvest storage and drying facilities ahead of the seasonal peak harvest."
        ]
    
    return YieldPredictionResponse(
        district=district_str,
        season=season_str,
        crop_name=crop_str,
        irrigation_zone_type=zone_str,
        predicted_yield_mt_ha=round(predicted_yield, 2),
        baseline_yield_mt_ha=round(baseline_yield, 2),
        yield_deficit_mt_ha=round(yield_deficit_mt_ha, 2),
        yield_deficit_percentage=round(yield_deficit_pct, 1),
        hazard_risk_level=risk_level,
        risk_summary=summary,
        actionable_advisories=advisories,
        model_metadata={
            "model_architecture": "Adaptive Hybrid AI (3-Year Rolling Baseline + Attenuated Ridge Climate Shock)",
            "test_r2_score": 0.6023,
            "test_rmse_mt_ha": 3.8182,
            "test_mae_mt_ha": 1.8931,
            "version": "1.0.0",
            "damping_factor_applied": damping
        }
    )
