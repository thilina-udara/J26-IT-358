from datetime import date,datetime
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.schemas.cultivation_plan import Crop,District

class ProductionEvidence(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    crop: Crop
    district: District
    season: Literal['Maha','Yala']
    reference: str=Field(min_length=1)
    verified: bool=False
    available_at: datetime
    verified_at: datetime
    valid_from: date
    valid_to: date
    applicable_without_variety_or_product: bool=False
    yield_kg_per_acre: float=Field(gt=0,allow_inf_nan=False)
    reference_window_production_kg: list[float]=Field(min_length=2)
    historical_observation_end: date
    reference_definition: str=Field(min_length=1)
    comparable_coverage_verified: bool=False
    quantile_method_approved_for_experiment: bool=False
    harvest_half_window_days: Literal[14]=14
    @model_validator(mode='after')
    def validate_evidence(self):
        import math
        if self.available_at.tzinfo is None or self.verified_at.tzinfo is None:raise ValueError('Aware evidence times required')
        if self.valid_to<self.valid_from:raise ValueError('Invalid validity interval')
        if any(not math.isfinite(v) or v<=0 for v in self.reference_window_production_kg):raise ValueError('Invalid reference production')
        return self

class SeasonAssignment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    plan_id: str
    updated_at: datetime
    season: Literal['Maha','Yala']
    verified: bool=False
    reference: str=Field(min_length=1)
    available_at: datetime
    @model_validator(mode='after')
    def aware(self):
        if self.updated_at.tzinfo is None or self.available_at.tzinfo is None:raise ValueError('Aware assignment times required')
        return self

class ProductionRegistry(BaseModel):
    model_config=ConfigDict(extra='forbid')
    evidence: list[ProductionEvidence]=Field(default_factory=list)
    season_assignments: list[SeasonAssignment]=Field(default_factory=list)
