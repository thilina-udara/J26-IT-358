"""Explicit human attestations; defaults never confer approval."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.expert_review import ExpertCase

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class ReviewerRegistration(Strict):
    reviewer_id: str=Field(min_length=1)
    credential_evidence: str=Field(min_length=1)
    agricultural_role: str=Field(min_length=1)
    organization: str=Field(min_length=1)
    verified: bool=False
    can_adjudicate: bool=False

class RubricRegistration(Strict):
    rubric_version: str=Field(min_length=1)
    rubric_text: str=Field(min_length=1)
    approved: bool=False
    approval_evidence: str | None=None

class CaseRegistration(Strict):
    case: ExpertCase
    case_version: int=Field(ge=1)
    snapshot_id: str=Field(min_length=1)
    dependence_group: str=Field(min_length=1)
    maximum_input_available_at: datetime
    provenance: Literal['verified_real','unknown','fictional']='unknown'
    provenance_evidence: str | None=None
    consent_evidence: str | None=None
    privacy_approval_evidence: str | None=None
    season_mapping_evidence: str | None=None
    @model_validator(mode='after')
    def cutoff(self):
        if self.maximum_input_available_at.tzinfo is None or self.maximum_input_available_at>self.case.forecast_cutoff:
            raise ValueError('Input availability must be aware and no later than cutoff')
        return self

class GovernedReview(Strict):
    case_version: int=Field(ge=1)
    case_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
    rubric_version: str=Field(min_length=1)
    label: Literal['Low','Medium','High','Uncertain']
    justification: str=Field(min_length=1,max_length=3000)
    reviewed_at: datetime

class Adjudication(Strict):
    case_version: int=Field(ge=1)
    rubric_version: str=Field(min_length=1)
    decision: Literal['Low','Medium','High','Uncertain','unresolved']
    justification: str=Field(min_length=1,max_length=3000)
