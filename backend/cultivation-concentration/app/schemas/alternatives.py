"""Scenario inputs and server-managed evidence contracts."""
from datetime import date,datetime
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from app.schemas.cultivation_plan import Crop,District


class AlternativeRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    selected_crop: Crop
    district: District
    region: str=Field(min_length=1,max_length=100)
    land_size_acres: float=Field(gt=0,allow_inf_nan=False)
    planting_date: date
    expected_harvest_date: date
    as_of: datetime | None=None
    replacing_plan_id: str | None=None

    @field_validator('region')
    @classmethod
    def normalize(cls,value):
        return ' '.join(value.split()).casefold()

    @model_validator(mode='after')
    def dates(self):
        if self.expected_harvest_date<self.planting_date:
            raise ValueError('Harvest cannot precede planting')
        return self


class Evidence(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    evidence_id: str=Field(min_length=1)
    crop: Crop
    district: District
    region: str=Field(min_length=1)
    source_reference: str=Field(min_length=1)
    verified_by: str=Field(min_length=1)
    verified_at: datetime
    available_at: datetime
    valid_from: date
    valid_to: date
    verified: bool=False

    @field_validator('region')
    @classmethod
    def normalize(cls,value):
        return ' '.join(value.split()).casefold()

    @model_validator(mode='after')
    def dates(self):
        if self.available_at.tzinfo is None or self.verified_at.tzinfo is None:
            raise ValueError('Evidence timestamps require timezones')
        if self.valid_to<self.valid_from:
            raise ValueError('Invalid evidence validity interval')
        return self


class SuitabilityEvidence(Evidence):
    min_land_acres: float=Field(ge=0,allow_inf_nan=False)
    max_land_acres: float=Field(gt=0,allow_inf_nan=False)
    min_harvest_days: int=Field(ge=0)
    max_harvest_days: int=Field(ge=0)
    applicability_statement: str=Field(min_length=1)
    # True only after an officer establishes applicability using these inputs;
    # generic soil/water-dependent guidance alone is insufficient.
    applicable_without_additional_inputs: bool=False

    @model_validator(mode='after')
    def bounds(self):
        if self.max_land_acres<self.min_land_acres or self.max_harvest_days<self.min_harvest_days:
            raise ValueError('Invalid suitability bounds')
        return self


class CoverageEvidence(Evidence):
    comparable_registration_scope: bool=False
    registration_scope_id: str=Field(min_length=1)
    coverage_statement: str=Field(min_length=1)


class EvidenceRegistry(BaseModel):
    model_config=ConfigDict(extra='forbid')
    suitability: list[SuitabilityEvidence]=Field(default_factory=list)
    coverage: list[CoverageEvidence]=Field(default_factory=list)
