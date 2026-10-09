"""Anonymized cases and submitted reviews, separate from provisional targets."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator


class Scenario(BaseModel):
    model_config=ConfigDict(extra='forbid')
    district: Literal['Matara','Hambantota']
    crop: Literal['Mung Beans','Corn','Bandakka','Brinjal','Pumpkin','Chillies']
    season: Literal['Maha','Yala']
    harvest_month: str=Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')
    season_verified: bool=False


class ClusterAggregate(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    farmer_count: int=Field(ge=3)
    plan_count: int=Field(ge=3)
    planned_acreage: float=Field(gt=0)


class ReviewIndicators(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    overlapping_farmer_count: int=Field(ge=3)
    overlapping_plan_count: int=Field(ge=3)
    total_planned_acreage: float=Field(gt=0)
    harvest_overlap_intensity: float=Field(ge=0,le=1)
    estimated_production_kg: float | None=None
    historical_concentration_baseline: float | None=None
    district_kmeans_groups: list[ClusterAggregate]=Field(default_factory=list)
    district_dbscan_groups: list[ClusterAggregate]=Field(default_factory=list)
    cluster_scope: Literal['district_context_not_target_membership']='district_context_not_target_membership'
    # Fixed current missing-evidence contract prevents invented numbers in exports.
    @model_validator(mode='after')
    def unavailable(self):
        if self.estimated_production_kg is not None or self.historical_concentration_baseline is not None:
            raise ValueError('Production and historical evidence unavailable in current contract')
        if self.overlapping_farmer_count>self.overlapping_plan_count:
            raise ValueError('Farmers cannot exceed plans')
        return self


class ExpertCase(BaseModel):
    model_config=ConfigDict(extra='forbid')
    case_id: str
    schema_version: Literal['phase3b-v1']='phase3b-v1'
    forecast_cutoff: datetime
    scenario: Scenario
    indicators: ReviewIndicators
    missing_evidence: list[str]
    reference_label: None=None
    provisional_rule_label: None=None

    @model_validator(mode='after')
    def cutoff_aware(self):
        if self.forecast_cutoff.tzinfo is None:
            raise ValueError('Cutoff requires timezone')
        return self


class ExpertReview(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    case_id: str
    case_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
    label_kind: Literal['expert_reference']='expert_reference'
    reference_label: Literal['Low','Medium','High','Uncertain']
    reason: str=Field(min_length=1,max_length=3000)
    reviewer_id: str=Field(min_length=1,max_length=100)
    reviewer_role: str=Field(min_length=1,max_length=100)
    reviewer_organization: str=Field(min_length=1,max_length=200)
    reviewed_at: datetime
    rubric_version: str=Field(min_length=1,max_length=100)
    @model_validator(mode='after')
    def timezone_required(self):
        if self.reviewed_at.tzinfo is None:
            raise ValueError('Review time requires timezone')
        return self
