from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import PriceType, validate_crop_id_value, validate_district_id_value


class MarketPriceBase(BaseModel):
    """Base schema for commodity market price points."""
    crop_id: str = Field(..., description="Crop identifier (e.g., 'CR_TOMATO')")
    market_id: str = Field(..., description="Selling market identifier (e.g., 'DEC_DAMBULLA')")
    market_name: str = Field(..., description="Human-readable market name")
    district_id: Optional[str] = Field(None, description="Host district code if known (e.g., 'LK-22')")
    price_date: date = Field(..., description="Date of price observation")
    price_type: PriceType = Field(default=PriceType.WHOLESALE, description="Wholesale, retail, or farmgate")
    price: Decimal = Field(..., gt=Decimal("0.0"), description="Observed price per unit in LKR")
    unit: str = Field(default="kg", description="Measurement unit")
    currency: str = Field(default="LKR", description="Currency ISO code")
    volume_traded_kg: Optional[Decimal] = Field(None, ge=Decimal("0.0"), description="Optional observed trade volume in kg")
    price_grade: Optional[str] = Field(default="Standard", description="Quality grade classification")
    data_source: str = Field(..., min_length=2, description="Origin source of price information")
    data_quality_flag: str = Field(default="verified", description="Data verification state (verified/provisional/flagged)")
    notes: Optional[str] = Field(None, description="Contextual market observations")

    @field_validator("crop_id")
    @classmethod
    def check_crop(cls, v: str) -> str:
        return validate_crop_id_value(v)

    @field_validator("district_id")
    @classmethod
    def check_district(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_district_id_value(v)
        return v


class MarketPriceCreate(MarketPriceBase):
    """Payload schema for submitting historical price records."""
    pass


class MarketPriceResponse(MarketPriceBase):
    """Response representation of an individual market price record."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
