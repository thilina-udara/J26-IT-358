"""
Data Schemas for Crop Yield Prediction and Explainable AI (XAI)

What this file does:
1. Defines the input structure (what the user or frontend sends).
2. Defines the output structure (what our AI model returns, including yield, advisories, and XAI).
3. Strictly limits crops to 7 approved non-paddy crops in Sri Lanka.
   Note: Pumpkin refers to Department of Census and Statistics Pumpkin. Ash Pumpkin is excluded.
4. Makes current_growth_stage optional so Component 4 never guesses sowing dates.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DistrictEnum(str, Enum):
    """The 25 administrative districts of Sri Lanka."""
    AMPARA = "Ampara"
    ANURADHAPURA = "Anuradhapura"
    BADULLA = "Badulla"
    BATTICALOA = "Batticaloa"
    COLOMBO = "Colombo"
    GALLE = "Galle"
    GAMPAHA = "Gampaha"
    HAMBANTOTA = "Hambantota"
    JAFFNA = "Jaffna"
    KALUTARA = "Kalutara"
    KANDY = "Kandy"
    KEGALLE = "Kegalle"
    KILINOCHCHI = "Kilinochchi"
    KURUNEGALA = "Kurunegala"
    MANNAR = "Mannar"
    MATALE = "Matale"
    MATARA = "Matara"
    MONARAGALA = "Monaragala"
    MULLAITIVU = "Mullaitivu"
    NUWARA_ELIYA = "Nuwara Eliya"
    POLONNARUWA = "Polonnaruwa"
    PUTTALAM = "Puttalam"
    RATNAPURA = "Ratnapura"
    TRINCOMALEE = "Trincomalee"
    VAVUNIYA = "Vavuniya"


class SeasonEnum(str, Enum):
    """The two main cultivation seasons in Sri Lanka."""
    MAHA = "Maha"
    YALA = "Yala"


class CropEnum(str, Enum):
    """
    The 7 approved study crops.
    Pumpkin refers to DCS Pumpkin. Ash Pumpkin (Alupuhul) is strictly excluded.
    """
    MAIZE = "Maize"
    CHILLI = "Chilli"
    GREEN_GRAM = "Green Gram"
    TOMATO = "Tomato"
    BRINJAL = "Brinjal"
    OKRA = "Okra"
    PUMPKIN = "Pumpkin"


class IrrigationZoneEnum(str, Enum):
    """Irrigation scheme classification."""
    MAJOR_IRRIGATION = "Major Irrigation"
    MINOR_RAINFED = "Minor / Rainfed"


class HazardRiskLevel(str, Enum):
    """Hazard risk levels based on climate stress and yield impact."""
    NORMAL = "NORMAL"
    MODERATE_STRESS = "MODERATE_STRESS"
    SEVERE_DROUGHT_RISK = "SEVERE_DROUGHT_RISK"
    EXCESS_WATER_FLOOD_RISK = "EXCESS_WATER_FLOOD_RISK"


class YieldPredictionRequest(BaseModel):
    """
    Input data needed to predict crop yield and check climate risks.
    """
    district: DistrictEnum = Field(
        ...,
        description="Administrative district in Sri Lanka (1 of 25 districts)",
        examples=["Puttalam"]
    )
    season: SeasonEnum = Field(
        ...,
        description="Cultivation season: Maha (NE Monsoon) or Yala (SW Monsoon)",
        examples=["Yala"]
    )
    crop_name: CropEnum = Field(
        ...,
        description="Target crop (strictly 1 of 7 approved crops; Pumpkin refers to DCS Pumpkin)",
        examples=["Maize"]
    )
    irrigation_zone_type: IrrigationZoneEnum = Field(
        ...,
        description="Water availability zone: Major Irrigation or Minor / Rainfed",
        examples=["Minor / Rainfed"]
    )
    rainfall_growing_season_total_mm: float = Field(
        ...,
        ge=0.0,
        le=5000.0,
        description="Total growing season rainfall in millimeters (from CHIRPS / Met Dept)",
        examples=[475.0]
    )
    temp_growing_season_mean_c: float = Field(
        ...,
        ge=10.0,
        le=45.0,
        description="Average growing season air temperature in degrees Celsius (from ERA5-Land)",
        examples=[28.3]
    )
    soil_moisture_growing_season_min: float = Field(
        ...,
        ge=0.01,
        le=1.0,
        description="Lowest root-zone soil moisture level during the season (m3/m3)",
        examples=[0.203]
    )
    spi3_growing_season_worst: float = Field(
        ...,
        ge=-5.0,
        le=5.0,
        description="Worst 3-month SPI drought index during the season (negative means dry, positive means wet)",
        examples=[-1.84]
    )
    current_growth_stage: Optional[str] = Field(
        None,
        description="Optional growth stage sent from the crop planning component. If not given, whole-season sensitivity is checked.",
        examples=["Flowering"]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "district": "Puttalam",
                "season": "Yala",
                "crop_name": "Maize",
                "irrigation_zone_type": "Minor / Rainfed",
                "rainfall_growing_season_total_mm": 475.0,
                "temp_growing_season_mean_c": 28.3,
                "soil_moisture_growing_season_min": 0.203,
                "spi3_growing_season_worst": -1.84,
                "current_growth_stage": None
            }
        }
    }


class FeatureAttribution(BaseModel):
    """
    Shows how a single feature (like rainfall or temperature) changed the predicted yield.
    Uses Linear SHAP: attribution = weight * (feature_value - average_value).
    """
    feature_name: str = Field(..., description="System feature name")
    display_name: str = Field(..., description="Simple readable feature name")
    feature_value: float = Field(..., description="Value for this prediction")
    reference_mean: float = Field(..., description="Historical average value in training data (2001-2020)")
    raw_shock_attribution_mt_ha: float = Field(
        ...,
        description="Raw change in yield caused by this feature in Metric Tons per Hectare"
    )
    damped_attribution_mt_ha: float = Field(
        ...,
        description="Attribution after applying crop damping factor (e.g. Maize damping = 0.0)"
    )
    impact_direction: str = Field(
        ...,
        description="Effect on yield: POSITIVE_BOOST (increases yield), NEGATIVE_DRAG (lowers yield), or NEUTRAL"
    )


class ExplainabilityBreakdown(BaseModel):
    """
    Full Explainable AI (XAI) breakdown.
    Explains the baseline yield and weather shock separately, and proves they add up to the final yield.
    """
    attribution_method: str = Field(
        default="Linear SHAP (Marginal Empirical Background, Inter-Feature Independence)",
        description="Explainability method used for the Ridge shock model"
    )
    mathematical_decomposition: str = Field(
        default="Y_pred = max(0.05, Y_baseline + gamma_crop * (E[Delta_shock] + sum(w_i * (x_i - E[X_i]))))",
        description="Simple math formula showing how the parts add up to the final yield"
    )
    baseline_reference_period: str = Field(
        default="2001 - 2020 Chronological Training Benchmark (N=6,355)",
        description="Historical benchmark period used for feature averages"
    )
    methodology_assumptions: List[str] = Field(
        default_factory=lambda: [
            "Shapley efficiency holds: the sum of feature attributions exactly equals the climate shock.",
            "Attributions show historical statistical relationships with yield, not direct laboratory proof.",
            "Maize damping factor (0.0) prevents confusing weather with the 2021-2022 fertilizer shortage.",
            "Baseline yield represents the 3-year historical average for this crop and district before the weather shock."
        ],
        description="Key assumptions behind the explanations"
    )
    
    # 1. Historical baseline
    historical_baseline_yield_mt_ha: float = Field(
        ...,
        description="Historical benchmark yield based on previous seasons (MT/ha)"
    )
    
    # 2. Climate shock baseline
    expected_climate_shock_mt_ha: float = Field(
        ...,
        description="Expected climate shock under normal average weather (MT/ha)"
    )
    crop_damping_factor: float = Field(
        ...,
        description="Crop damping factor: 1.0 for vegetables/pulses, 0.0 for Maize"
    )
    
    # 3. Weather features
    climate_feature_attributions: List[FeatureAttribution] = Field(
        default_factory=list,
        description="Attributions for rainfall, temperature, soil moisture, and SPI-3"
    )
    
    # 4. Context features (district, season, crop, zone)
    context_feature_attributions: List[FeatureAttribution] = Field(
        default_factory=list,
        description="Attributions for district, season, crop type, and irrigation zone"
    )
    
    # 5. Math reconciliation check
    total_climate_shock_impact_mt_ha: float = Field(
        ...,
        description="Net weather impact added to baseline yield (MT/ha)"
    )
    unclamped_hybrid_yield_mt_ha: float = Field(
        ...,
        description="Direct sum of baseline yield and total weather shock (MT/ha)"
    )
    clamping_adjustment_mt_ha: float = Field(
        default=0.0,
        description="Adjustment applied if prediction fell below the minimum 0.05 MT/ha limit"
    )
    final_reconciled_yield_mt_ha: float = Field(
        ...,
        description="Reconciled prediction that exactly matches predicted_yield_mt_ha"
    )
    is_explanation_consistent: bool = Field(
        True,
        description="True if the sum of parts matches the predicted yield within rounding tolerance"
    )


class YieldPredictionResponse(BaseModel):
    """
    Response returned by the yield prediction API.
    Includes predicted yield, deficit percentage, farm advisories, and XAI explanation.
    """
    district: str = Field(..., description="Target district")
    season: str = Field(..., description="Cultivation season")
    crop_name: str = Field(..., description="Target crop (strictly Pumpkin; Ash Pumpkin excluded)")
    irrigation_zone_type: str = Field(..., description="Irrigation scheme type")
    growth_stage_evaluated: str = Field(
        default="General Whole-Season Sensitivity Profile",
        description="Shows if whole season or a specific growth stage was evaluated"
    )
    
    # Yield numbers
    predicted_yield_mt_ha: float = Field(
        ...,
        description="Predicted crop yield in Metric Tons per Hectare (MT/ha)"
    )
    baseline_yield_mt_ha: float = Field(
        ...,
        description="Normal historical baseline yield for this district and crop (MT/ha)"
    )
    yield_deficit_mt_ha: float = Field(
        ...,
        description="Yield difference (predicted - baseline). Negative number means a yield loss."
    )
    yield_deficit_percentage: float = Field(
        ...,
        description="Percentage change compared to normal baseline: ((predicted - baseline) / baseline) * 100"
    )
    
    # Risk and advisories
    hazard_risk_level: HazardRiskLevel = Field(
        ...,
        description="Hazard risk level (NORMAL, MODERATE_STRESS, SEVERE_DROUGHT_RISK, EXCESS_WATER_FLOOD_RISK)"
    )
    risk_summary: str = Field(
        ...,
        description="Clear summary of climate risks and expected impact on the crop"
    )
    actionable_advisories: List[str] = Field(
        default_factory=list,
        description="Helpful farm management tips for agricultural extension officers and farmers"
    )
    
    # Explainable AI
    explainability: ExplainabilityBreakdown = Field(
        ...,
        description="Easy-to-understand breakdown showing how each weather factor influenced the prediction"
    )
    
    # Model metadata
    model_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model architecture, version, and performance metrics"
    )
