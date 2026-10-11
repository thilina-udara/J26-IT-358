"""Validated plan inputs and privacy-preserving response types."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

District = Literal['Matara', 'Hambantota']
Crop = Literal['Mung Beans', 'Corn', 'Bandakka', 'Brinjal', 'Pumpkin', 'Chillies']
Season = Literal['Maha', 'Yala']


class PlanInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    farmer_id: str = Field(min_length=1, max_length=100)
    district: District
    region: str = Field(min_length=1, max_length=100)
    crop: Crop
    land_size_acres: float = Field(gt=0, allow_inf_nan=False)
    planting_date: date
    expected_harvest_date: date
    farmer_declared_season: Season | None = Field(default=None,
        description='Farmer declaration only; not an independently verified statistical season')
    status: Literal['active', 'cancelled'] = 'active'

    @field_validator('region')
    @classmethod
    def canonical_region(cls, value):
        return ' '.join(value.split()).casefold()

    @model_validator(mode='after')
    def chronological_dates(self):
        if self.expected_harvest_date < self.planting_date:
            raise ValueError('Expected harvest cannot precede planting')
        return self


class Plan(PlanInput):
    plan_id: str
    submitted_at: datetime
    updated_at: datetime


class PlanSubmission(PlanInput):
    """HTTP input: identity comes from auth; optional legacy assertion must match."""
    farmer_id: str | None = Field(default=None, min_length=1, max_length=100)


class Concentration(BaseModel):
    plan_count: int | None = None
    total_acreage: float | None = None
    status: str = 'suppressed_for_privacy'
    harvest_window_start: date
    harvest_window_end: date
    data_coverage_warning: str


class PlanResponse(BaseModel):
    plan: Plan
    concentration: Concentration


class PlanListResponse(BaseModel):
    """Current owned records only; historical versions stay in existing stores."""
    items: list[Plan]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0, le=1_000_000)
    has_more: bool
    next_offset: int | None
