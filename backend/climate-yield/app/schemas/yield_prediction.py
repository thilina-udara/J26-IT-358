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
    crop_year: Optional[int] = Field(
        None,
        ge=2001,
        le=2030,
        description="Optional crop year for historical evaluation or reference (e.g., 2021-2025). If provided, looks up historical rolling baseline.",
        examples=[2023]
    )
    baseline_yield_mt_ha: Optional[float] = Field(
        None,
        ge=0.01,
        le=150.0,
        description="Optional custom or observed baseline yield (MT/ha). If omitted, uses district-crop 3-year rolling agronomic baseline.",
        examples=[12.50]
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
            "Maize damping factor (0.0) isolates non-climatic macro input shocks, ensuring climate attributions remain purely weather-driven.",
            "Baseline yield represents the 3-year historical average for this crop and district before the weather shock."
        ],
        description="Key assumptions behind the explanations"
    )
    
    baseline_type: str = Field(
        default="DYNAMIC_ROLLING_3YR_BASELINE",
        description="Source of baseline yield: HISTORICAL_ROLLING_3YR_BASELINE, LATEST_ROLLING_3YR_BASELINE, DISTRICT_CROP_HISTORICAL_MEAN_FALLBACK, or CUSTOM_SUPPLIED_BASELINE"
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
    
    baseline_type: str = Field(
        default="DYNAMIC_ROLLING_3YR_BASELINE",
        description="Source of baseline yield used for prediction (rolling baseline or fallback)"
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
    pure_rolling_baseline_test_r2: float = Field(
        default=0.6138,
        description="Benchmark test R2 for pure 3-year rolling baseline alone"
    )
    hybrid_model_test_r2: float = Field(
        default=0.6023,
        description="Benchmark test R2 for climate-adjusted Adaptive Hybrid AI model"
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


class IntegratedDecisionSupportRequest(BaseModel):
    """
    Request model for the Full Decision Support System (DSS):
    Integrates 14-day climate hazard early warning, phenological vulnerability,
    and seasonal crop yield deficit prediction with Linear SHAP explainability.
    """
    district: DistrictEnum = Field(
        ...,
        description="Target district in Sri Lanka (1 of 25 official districts)",
        examples=["Anuradhapura"]
    )
    crop_name: CropEnum = Field(
        ...,
        description="Target crop (strictly 1 of 7 approved study crops)",
        examples=["Maize"]
    )
    season: SeasonEnum = Field(
        ...,
        description="Cultivation season: Maha (NE Monsoon) or Yala (SW Monsoon)",
        examples=["Maha"]
    )
    irrigation_zone_type: IrrigationZoneEnum = Field(
        ...,
        description="Water availability zone: Major Irrigation or Minor / Rainfed",
        examples=["Major Irrigation"]
    )
    rainfall_growing_season_total_mm: float = Field(
        ...,
        ge=0.0,
        le=5000.0,
        description="Total growing season rainfall in mm (from CHIRPS / Met Dept)",
        examples=[850.0]
    )
    temp_growing_season_mean_c: float = Field(
        ...,
        ge=10.0,
        le=45.0,
        description="Average growing season temperature in °C (from ERA5-Land)",
        examples=[28.5]
    )
    soil_moisture_growing_season_min: float = Field(
        ...,
        ge=0.01,
        le=1.0,
        description="Lowest root-zone volumetric soil moisture level during the season (m³/m³)",
        examples=[0.215]
    )
    spi3_growing_season_worst: float = Field(
        ...,
        ge=-5.0,
        le=5.0,
        description="Worst 3-month SPI drought index during the season",
        examples=[-0.85]
    )
    current_growth_stage: Optional[str] = Field(
        None,
        description="Optional crop growth stage (e.g., Flowering, Pod Setting). If omitted, evaluates general whole-season sensitivity.",
        examples=["Flowering"]
    )
    crop_year: Optional[int] = Field(
        None,
        ge=2001,
        le=2030,
        description="Optional crop year for historical walk-forward baseline lookup",
        examples=[2023]
    )
    baseline_yield_mt_ha: Optional[float] = Field(
        None,
        ge=0.01,
        le=150.0,
        description="Optional custom baseline yield (MT/ha). If omitted, looks up 3-year rolling agronomic baseline.",
        examples=[4.20]
    )
    include_live_14day_forecast: bool = Field(
        True,
        description="Whether to query the live 14-day weather forecast API for real-time hazard screening"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "district": "Anuradhapura",
                "crop_name": "Maize",
                "season": "Maha",
                "irrigation_zone_type": "Major Irrigation",
                "rainfall_growing_season_total_mm": 850.0,
                "temp_growing_season_mean_c": 28.5,
                "soil_moisture_growing_season_min": 0.215,
                "spi3_growing_season_worst": -0.85,
                "current_growth_stage": "Flowering",
                "include_live_14day_forecast": True
            }
        }
    }


class IntegratedDecisionSupportResponse(BaseModel):
    """
    Comprehensive output of the Component 4 Decision Support System (DSS):
    Unites 14-Day Climate Hazard Screening, Crop Phenology Vulnerability,
    Seasonal Yield Deficit Impact, and Linear SHAP Explainability.
    """
    system_title: str = Field(
        default="AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System",
        description="Component 4 official system title"
    )
    timestamp_utc: str = Field(..., description="UTC timestamp of the decision support assessment")
    
    # Query Identification
    district: str = Field(..., description="Target district")
    crop_name: str = Field(..., description="Target crop")
    season: str = Field(..., description="Cultivation season")
    irrigation_zone_type: str = Field(..., description="Irrigation scheme")
    growth_stage_evaluated: str = Field(..., description="Growth stage evaluated")

    # Layer 1: Operational 14-Day Climate Hazard Early Warning
    layer1_climate_early_warning_14day: Dict[str, Any] = Field(
        ...,
        description="14-day forward climate hazard screening (rainfall, dry spell, heat alert)"
    )

    # Layer 2: Crop Phenological Vulnerability Assessment
    layer2_phenology_vulnerability: Dict[str, Any] = Field(
        ...,
        description="Intersection of 14-day forecast with crop heat and waterlogging sensitivity"
    )

    # Layer 3: Seasonal Crop Yield Deficit Prediction
    layer3_seasonal_yield_impact: Dict[str, Any] = Field(
        ...,
        description="Macro-seasonal harvest yield projection, baseline, and deficit percentage"
    )

    # Layer 4: Explainable AI (XAI) Attribution
    layer4_explainability_xai: ExplainabilityBreakdown = Field(
        ...,
        description="Linear SHAP feature attribution proving exact mathematical reconciliation"
    )

    # Actionable Field Advisories (Water, Drainage, Canopy Protection only)
    actionable_decision_support_advisories: List[str] = Field(
        default_factory=list,
        description="Prioritized agronomic water management and protective advisories"
    )

    # System Governance & Boundaries
    system_governance_and_boundaries: Dict[str, Any] = Field(
        default_factory=dict,
        description="Explicit scope disclosure (zero fertilizer, zero crop selection, zero sowing date estimation)"
    )


class EarlyWarningRiskProbabilities(BaseModel):
    """Calibrated Softmax probability distribution from Model 1 multi-hazard classifier."""
    Normal: float = Field(..., description="Probability of Normal / Low Risk conditions (Tier 0)")
    Moderate: float = Field(..., description="Probability of Moderate Alert conditions (Tier 1)")
    Severe: float = Field(..., description="Probability of Severe Alert conditions (Tier 2)")
    Extreme: float = Field(..., description="Probability of Extreme Crisis conditions (Tier 3)")


class EarlyWarningClassifierOutput(BaseModel):
    """Detailed output from Model 1 (AI-Powered Climate Early Warning Multi-Hazard Classifier)."""
    status: str = Field(..., description="Execution status of the classifier")
    predicted_risk_tier: Optional[int] = Field(None, ge=0, le=3, description="Predicted hazard risk tier (0=Normal, 1=Moderate, 2=Severe, 3=Extreme)")
    risk_tier_name: str = Field(..., description="Official descriptive name of the predicted hazard risk tier")
    risk_probabilities: Optional[EarlyWarningRiskProbabilities] = Field(None, description="Softmax probability distribution across tiers")
    dominant_hazard_probability_pct: Optional[float] = Field(None, description="Confidence percentage for the winning tier")
    input_features_summary: Optional[Dict[str, Any]] = Field(None, description="Summary of input meteorological and soil indicators")
    model_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata describing trained XGBoost classifier and validation metrics")
    hazard_interpretation: str = Field(..., description="Plain English agronomic interpretation of hazard risks")


class EarlyWarningClassifyRequest(BaseModel):
    """Direct input vector for testing or simulating 14-day climate hazard risk classification."""
    district: DistrictEnum = Field(..., description="Target district in Sri Lanka (1 of 25 official districts)", examples=["Anuradhapura"])
    rainfall_14d_sum_mm: float = Field(..., ge=0.0, le=3000.0, description="14-day cumulative rainfall in mm", examples=[85.0])
    rainfall_max_1d_mm: float = Field(..., ge=0.0, le=1000.0, description="Peak single-day rainfall in mm", examples=[25.0])
    temp_max_14d_peak_c: float = Field(..., ge=5.0, le=55.0, description="Peak daily maximum temperature in °C", examples=[33.0])
    temp_mean_14d_c: float = Field(..., ge=5.0, le=45.0, description="Mean temperature across the 14-day window in °C", examples=[28.0])
    temp_min_14d_c: float = Field(..., ge=0.0, le=40.0, description="Minimum daily temperature in °C", examples=[23.5])
    humidity_mean_pct: float = Field(75.0, ge=10.0, le=100.0, description="Average relative humidity percentage", examples=[78.0])
    consecutive_heat_days: int = Field(0, ge=0, le=14, description="Consecutive days with Tmax >= 35°C", examples=[0])
    consecutive_dry_days: int = Field(0, ge=0, le=14, description="Consecutive dry days (rain < 1.0 mm)", examples=[3])
    soil_moisture_topsoil_m3_m3: float = Field(0.25, ge=0.0, le=1.0, description="Volumetric topsoil root-zone moisture (m³/m³)", examples=[0.26])
    spi3_current: float = Field(0.0, ge=-5.0, le=5.0, description="Current 3-month Standardized Precipitation Index (SPI-3)", examples=[-0.2])
    month: Optional[int] = Field(None, ge=1, le=12, description="Calendar month (1 to 12)", examples=[10])
