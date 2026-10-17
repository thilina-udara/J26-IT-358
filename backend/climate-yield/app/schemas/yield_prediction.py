"""
Pydantic Schemas for Climate Hazard & Crop Yield Impact Prediction
Component 4: AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DistrictEnum(str, Enum):
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
    MAHA = "Maha"
    YALA = "Yala"


class CropEnum(str, Enum):
    MAIZE = "Maize"
    CHILLI = "Chilli"
    GREEN_GRAM = "Green Gram"
    TOMATO = "Tomato"
    BRINJAL = "Brinjal"
    OKRA = "Okra"
    PUMPKIN = "Pumpkin"


class IrrigationZoneEnum(str, Enum):
    MAJOR_IRRIGATION = "Major Irrigation"
    MINOR_RAINFED = "Minor / Rainfed"


class HazardRiskLevel(str, Enum):
    NORMAL = "NORMAL"
    MODERATE_STRESS = "MODERATE_STRESS"
    SEVERE_DROUGHT_RISK = "SEVERE_DROUGHT_RISK"
    EXCESS_WATER_FLOOD_RISK = "EXCESS_WATER_FLOOD_RISK"


class YieldPredictionRequest(BaseModel):
    """
    Input payload for pre-harvest crop yield deficit prediction and climate risk evaluation.
    """
    district: DistrictEnum = Field(
        ...,
        description="Administrative district of Sri Lanka (1 of 25 districts)",
        examples=["Puttalam"]
    )
    season: SeasonEnum = Field(
        ...,
        description="Cultivation season: Maha (NE Monsoon) or Yala (SW Monsoon)",
        examples=["Yala"]
    )
    crop_name: CropEnum = Field(
        ...,
        description="Target crop strictly limited to the 7 approved study crops",
        examples=["Maize"]
    )
    irrigation_zone_type: IrrigationZoneEnum = Field(
        ...,
        description="Command irrigation zone classification",
        examples=["Minor / Rainfed"]
    )
    rainfall_growing_season_total_mm: float = Field(
        ...,
        ge=0.0,
        le=5000.0,
        description="Cumulative growing season rainfall in millimeters (CHIRPS / Met Dept)",
        examples=[475.0]
    )
    temp_growing_season_mean_c: float = Field(
        ...,
        ge=10.0,
        le=45.0,
        description="Mean growing season air temperature in degrees Celsius (ERA5-Land)",
        examples=[28.3]
    )
    soil_moisture_growing_season_min: float = Field(
        ...,
        ge=0.01,
        le=1.0,
        description="Minimum volumetric soil moisture content during critical growth stages (m3/m3)",
        examples=[0.203]
    )
    spi3_growing_season_worst: float = Field(
        ...,
        ge=-5.0,
        le=5.0,
        description="Worst 3-month Standardized Precipitation Index during the growing season (WMO index)",
        examples=[-1.84]
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
                "spi3_growing_season_worst": -1.84
            }
        }
    }


class YieldPredictionResponse(BaseModel):
    """
    Decision support response payload returning predicted yield, deficit impact, and actionable advisories.
    """
    district: str = Field(..., description="Target district")
    season: str = Field(..., description="Cultivation season")
    crop_name: str = Field(..., description="Target crop")
    irrigation_zone_type: str = Field(..., description="Irrigation scheme type")
    
    # Numerical Yield Attributions
    predicted_yield_mt_ha: float = Field(
        ...,
        description="AI-forecasted seasonal crop yield in Metric Tons per Hectare"
    )
    baseline_yield_mt_ha: float = Field(
        ...,
        description="Historical benchmark baseline yield under normal climate conditions"
    )
    yield_deficit_mt_ha: float = Field(
        ...,
        description="Absolute yield difference (predicted - baseline). Negative value denotes yield deficit."
    )
    yield_deficit_percentage: float = Field(
        ...,
        description="Percentage yield deficit relative to baseline: ((predicted - baseline) / baseline) * 100"
    )
    
    # Hazard Classification
    hazard_risk_level: HazardRiskLevel = Field(
        ...,
        description="Multi-hazard classification (NORMAL, MODERATE_STRESS, SEVERE_DROUGHT_RISK, EXCESS_WATER_FLOOD_RISK)"
    )
    risk_summary: str = Field(
        ...,
        description="Executive summary of the detected hazard and crop impact"
    )
    
    # Prescriptive Agro-Advisories
    actionable_advisories: List[str] = Field(
        default_factory=list,
        description="List of prescriptive agronomic mitigation measures for extension officers and farmers"
    )
    
    # Model Metadata
    model_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model architecture, confidence metrics, and execution metadata"
    )
