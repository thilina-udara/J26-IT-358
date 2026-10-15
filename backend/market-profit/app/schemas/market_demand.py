from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.common import DemandLevel, DemandRecordType, validate_crop_id_value, validate_district_id_value


class MarketDemandBase(BaseModel):
    """Base schema for commodity market demand records."""
    crop_id: str = Field(..., description="Crop identifier (e.g., 'CR_TOMATO')")
    district_id: str = Field(..., description="Consumption district code (e.g., 'LK-11')")
    market_id: Optional[str] = Field(None, description="Specific market center if demand is DEC-localized")
    period_start_date: date = Field(..., description="Start of demand observation window")
    period_end_date: date = Field(..., description="End of demand observation window")
    demand_volume_kg: Decimal = Field(..., gt=Decimal("0.0"), description="Demand volume in kilograms")
    unit: str = Field(default="kg", description="Measurement unit")
    record_type: DemandRecordType = Field(..., description="Provenance: observed, estimated, or synthetic")
    demand_level: Optional[DemandLevel] = Field(None, description="Categorical demand level (High, Medium, Low)")
    confidence_score: Optional[Decimal] = Field(
        None, ge=Decimal("0.0"), le=Decimal("1.0"),
        description="Confidence weighting between 0.0 and 1.0"
    )
    estimation_method: Optional[str] = Field(None, description="Estimation technique or synthetic model identifier")
    is_training_eligible: bool = Field(
        default=True,
        description="Flag indicating if record may be used in ML training sets (False for synthetic data)"
    )
    data_source: str = Field(..., min_length=2, description="Origin source / survey name")
    notes: Optional[str] = Field(None, description="Methodological notes")

    @field_validator("crop_id")
    @classmethod
    def check_crop(cls, v: str) -> str:
        return validate_crop_id_value(v)

    @field_validator("district_id")
    @classmethod
    def check_district(cls, v: str) -> str:
        return validate_district_id_value(v)

    @model_validator(mode="after")
    def validate_period_and_eligibility(self) -> "MarketDemandBase":
        if self.period_end_date < self.period_start_date:
            raise ValueError(
                f"period_end_date ({self.period_end_date}) cannot precede period_start_date ({self.period_start_date})"
            )
        # Synthetic data must never default to training-eligible to prevent model poisoning
        if self.record_type == DemandRecordType.SYNTHETIC and self.is_training_eligible:
            # Enforce safety rule
            self.is_training_eligible = False
        return self


class MarketDemandCreate(MarketDemandBase):
    """Payload schema for inserting new demand records."""
    pass


class MarketDemandResponse(MarketDemandBase):
    """Response representation of a market demand entry."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


from typing import List
from app.schemas.common import PaginationMeta


class PaginatedMarketDemandResponse(BaseModel):
    """Paginated collection of market demand records."""
    meta: PaginationMeta
    items: List[MarketDemandResponse]
