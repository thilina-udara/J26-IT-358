from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import (
    DemandLevel,
    PredictionStatus,
    STANDARD_MARKETS,
    validate_crop_id_value,
    validate_district_id_value,
    validate_market_id_value,
)


class DemandForecastRequest(BaseModel):
    """
    Input parameters for requesting an ML-ready market commodity demand forecast.
    Validates crop, district, and market against shared catalogs and requires a current or future date.
    """
    crop_id: str = Field(
        ...,
        description="Target agricultural crop identifier (e.g., 'CR_TOMATO')"
    )
    cultivation_district_id: str = Field(
        ...,
        description="Origin district where crop is grown (e.g., 'LK-71')"
    )
    target_market_id: str = Field(
        ...,
        description="Destination Dedicated Economic Centre / market hub (e.g., 'DEC_DAMBULLA')"
    )
    forecast_target_date: date = Field(
        ...,
        description="Target market arrival / harvest date (must not be in the past)"
    )

    @field_validator("crop_id")
    @classmethod
    def check_crop(cls, v: str) -> str:
        return validate_crop_id_value(v)

    @field_validator("cultivation_district_id")
    @classmethod
    def check_district(cls, v: str) -> str:
        return validate_district_id_value(v)

    @field_validator("target_market_id")
    @classmethod
    def check_market(cls, v: str) -> str:
        return validate_market_id_value(v)

    @field_validator("forecast_target_date")
    @classmethod
    def check_target_date(cls, v: date) -> date:
        today = date.today()
        if v < today:
            raise ValueError(
                f"forecast_target_date ({v}) cannot be in the past (before {today}). "
                "Forecasting requires a current or future target date."
            )
        return v


class DemandForecastResponse(BaseModel):
    """
    Standardized response contract for market demand forecasting.
    Projected metrics remain strictly null when prediction_status is 'unavailable'
    to prevent presenting fabricated or mock numbers as genuine ML predictions.
    """
    crop_id: str = Field(..., description="Target crop identifier")
    cultivation_district_id: str = Field(..., description="Cultivation district code")
    target_market_id: str = Field(..., description="Selling market identifier")
    target_market_name: Optional[str] = Field(None, description="Resolved human-readable market name")
    forecast_target_date: date = Field(..., description="Target forecast date")
    prediction_status: PredictionStatus = Field(
        default=PredictionStatus.UNAVAILABLE,
        description="Prediction lifecycle status ('pending', 'completed', 'unavailable', 'failed')"
    )
    projected_demand_volume_kg: Optional[Decimal] = Field(
        None,
        description="ML-predicted demand volume in kilograms (null when unavailable)"
    )
    projected_demand_level: Optional[DemandLevel] = Field(
        None,
        description="Categorical demand level: 'High', 'Medium', or 'Low' (null when unavailable)"
    )
    model_version: Optional[str] = Field(
        None,
        description="Trained model version tag (null when unavailable)"
    )
    model_provenance: Optional[Dict[str, Any]] = Field(
        None,
        description="Model architecture and metadata dictionary (null when unavailable)"
    )
    status_message: str = Field(
        default="Machine learning demand prediction model is currently offline or undergoing training.",
        description="Human-readable status or diagnostic explanation"
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when forecast was evaluated"
    )

    model_config = ConfigDict(from_attributes=True)
