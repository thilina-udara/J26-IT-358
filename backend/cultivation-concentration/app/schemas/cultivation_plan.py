"""Validated plan inputs and privacy-preserving response types."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

District = Literal['Matara', 'Hambantota']
Crop = Literal['Mung Beans', 'Corn', 'Bandakka', 'Brinjal', 'Pumpkin', 'Chillies']


class PlanInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    farmer_id: str = Field(min_length=1, max_length=100)
    district: District
    region: str = Field(min_length=1, max_length=100)
    crop: Crop
    land_size_acres: float = Field(gt=0, allow_inf_nan=False)
    planting_date: date
    expected_harvest_date: date
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
