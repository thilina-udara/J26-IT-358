"""Validated prospective inputs; forecast configuration is never farmer-supplied."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class AssessmentRequest(Strict):
    plan_id:str=Field(min_length=1)
    protocol_id:str|None=None

class Protocol(Strict):
    protocol_id:str=Field(min_length=1)
    target_kind:Literal['future_registered_concentration','independently_observed_realized_concentration']
    horizon_days:int=Field(ge=1,le=730)
    definition_version:str=Field(min_length=1)
    definition:str=Field(min_length=20)
    independent_outcome_evidence:str=Field(min_length=10)
    frozen_label_order:tuple[str,str,str]=('Low','Medium','High')
    @model_validator(mode='after')
    def labels(self):
        if self.frozen_label_order!=('Low','Medium','High'):raise ValueError('Fixed concentration labels required')
        return self

class Artifact(Strict):
    version:str=Field(min_length=1)
    sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    available_at:datetime
    evidence_reference:str=Field(min_length=1)
    @model_validator(mode='after')
    def aware(self):
        if self.available_at.tzinfo is None:raise ValueError('Aware artifact availability required')
        return self

class Forecast(Strict):
    status:Literal['experimental_forecast','unavailable']
    category:Literal['Low','Medium','High']|None=None
    model:Artifact|None=None
    historical_reference:Artifact|None=None
    target_definition_version:str|None=None
    reason:str|None=None
    @model_validator(mode='after')
    def evidence(self):
        if self.status=='experimental_forecast' and (self.category is None or self.model is None or self.historical_reference is None or not self.target_definition_version):
            raise ValueError('Forecast needs model, reference and target version')
        if self.status=='unavailable' and self.category is not None:raise ValueError('Unavailable forecast cannot have category')
        return self

class Outcome(Strict):
    assessment_id:str
    category:Literal['Low','Medium','High']
    target_definition_version:str
    observed_at:datetime
    evidence_reference:str=Field(min_length=10)
    evidence_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    independently_observed:Literal[True]
    derived_from_current_snapshot:Literal[False]
    @model_validator(mode='after')
    def aware(self):
        if self.observed_at.tzinfo is None:raise ValueError('Aware observation time required')
        return self
