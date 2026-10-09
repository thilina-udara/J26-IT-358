"""Future training record contract. Targets and audit metadata stay outside X."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

FEATURE_NAMES = ('district','region','crop','season','overlapping_farmer_count',
    'overlapping_plan_count','total_planned_acreage','harvest_overlap_intensity',
    'estimated_production_kg','historical_concentration_baseline',
    'kmeans_group_acreage','kmeans_group_farmer_count','kmeans_harvest_span_days',
    'dbscan_group_acreage','dbscan_group_farmer_count','dbscan_core_fraction')


class RiskFeatures(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    district: Literal['Matara','Hambantota']
    region: str=Field(min_length=1)
    crop: Literal['Mung Beans','Corn','Bandakka','Brinjal','Pumpkin','Chillies']
    season: Literal['Maha','Yala']
    overlapping_farmer_count: int=Field(ge=0)
    overlapping_plan_count: int=Field(ge=0)
    total_planned_acreage: float=Field(ge=0)
    harvest_overlap_intensity: float=Field(ge=0,le=1)
    estimated_production_kg: float | None=Field(None,ge=0)
    historical_concentration_baseline: float | None=Field(None,ge=0)
    kmeans_group_acreage: float | None=Field(None,ge=0)
    kmeans_group_farmer_count: int | None=Field(None,ge=0)
    kmeans_harvest_span_days: int | None=Field(None,ge=0)
    dbscan_group_acreage: float | None=Field(None,ge=0)
    dbscan_group_farmer_count: int | None=Field(None,ge=0)
    dbscan_core_fraction: float | None=Field(None,ge=0,le=1)


class LabelEvidence(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: Literal['observed_reference','provisional_rule','unlabeled']='unlabeled'
    value: Literal['Low','Medium','High'] | None=None
    evidence_reference: str | None=None
    definition_version: str | None=None
    reviewer: str | None=None

    @model_validator(mode='after')
    def require_evidence(self):
        if self.kind=='unlabeled':
            if self.value is not None:
                raise ValueError('Unlabeled records cannot contain a target')
        elif not self.value or not self.evidence_reference or not self.definition_version:
            raise ValueError('Labels require documented evidence and a versioned definition')
        if self.kind=='observed_reference' and not self.reviewer:
            raise ValueError('Reference labels require an accountable reviewer')
        return self


class TrainingRecord(BaseModel):
    model_config=ConfigDict(extra='forbid')
    snapshot_id: str
    forecast_cutoff: datetime
    maximum_input_available_at: datetime
    features: RiskFeatures
    label: LabelEvidence=Field(default_factory=LabelEvidence)

    @model_validator(mode='after')
    def time_safe(self):
        if self.forecast_cutoff.tzinfo is None or self.maximum_input_available_at.tzinfo is None:
            raise ValueError('Availability/cutoff require timezones')
        if self.maximum_input_available_at>self.forecast_cutoff:
            raise ValueError('Input unavailable at forecast cutoff')
        return self


def training_projection(records, allow_provisional=False):
    """Fail closed for absent or inappropriate labels; no fitting/export performed."""
    if not records:
        raise ValueError('No training records')
    if any(r.label.kind=='unlabeled' or (r.label.kind=='provisional_rule' and not allow_provisional) for r in records):
        raise ValueError('Reference labels required; provisional targets need explicit separate experiment')
    if len({r.snapshot_id for r in records})!=len(records):
        raise ValueError('Duplicate snapshot keys')
    return ([r.features.model_dump() for r in records],[r.label.value for r in records])
