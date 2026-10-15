from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import (
    PredictionStatus,
    STANDARD_MARKETS,
    validate_crop_id_value,
    validate_district_id_value,
    validate_market_id_value,
)


class ForecastPriceType(str, Enum):
    """Permitted price tiers for commodity forecasting: wholesale or retail."""
    WHOLESALE = "wholesale"
    RETAIL = "retail"


class PriceForecastRequest(BaseModel):
    """
    Input schema for requesting an ML-ready market commodity price forecast.
    Enforces distinct wholesale vs retail pricing and validates identifiers and target dates.
    """
    crop_id: str = Field(
        ...,
        description="Target agricultural crop identifier (e.g., 'CR_TOMATO')"
    )
    cultivation_district_id: str = Field(
        ...,
        description="District where crop is cultivated (e.g., 'LK-71')"
    )
    target_market_id: str = Field(
        ...,
        description="Target selling market center (e.g., 'DEC_DAMBULLA')"
    )
    forecast_target_date: date = Field(
        ...,
        description="Target forecast date (must not be in the past)"
    )
    price_type: ForecastPriceType = Field(
        default=ForecastPriceType.WHOLESALE,
        description="Price tier to forecast: 'wholesale' or 'retail'. Data and models must never be mixed."
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


class PriceForecastResponse(BaseModel):
    """
    Standardized response contract for commodity price forecasting.
    Forecasted price remains strictly null when prediction_status is 'unavailable'
    to prevent presenting fabricated or mock prices as genuine ML predictions.
    """
    crop_id: str = Field(..., description="Target crop identifier")
    cultivation_district_id: str = Field(..., description="Cultivation district code")
    target_market_id: str = Field(..., description="Selling market identifier")
    target_market_name: Optional[str] = Field(None, description="Resolved human-readable market name")
    forecast_target_date: date = Field(..., description="Target forecast date")
    price_type: ForecastPriceType = Field(..., description="Evaluated price tier ('wholesale' or 'retail')")
    currency: str = Field(default="LKR", description="Currency identifier (strictly 'LKR')")
    unit: str = Field(default="kg", description="Measurement unit (strictly 'kg')")
    prediction_status: PredictionStatus = Field(
        default=PredictionStatus.UNAVAILABLE,
        description="Prediction lifecycle status ('pending', 'completed', 'unavailable', 'failed')"
    )
    forecasted_price_lkr_per_kg: Optional[Decimal] = Field(
        None,
        description="ML-predicted price in LKR per kg (null when unavailable)"
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
        default="Machine learning price forecasting model is currently offline or undergoing training.",
        description="Human-readable status or diagnostic explanation"
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when forecast was evaluated"
    )

    model_config = ConfigDict(from_attributes=True)
