from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal
from app.schemas.cultivation_plan import Crop, District
from app.schemas.personalized_planning import PlanningRequest

class WorkflowPlan(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    crop: Crop
    district: District
    region: str=Field(default='unspecified',min_length=1,max_length=100)
    land_size_acres: float=Field(gt=0,allow_inf_nan=False)
    planting_date: date
    expected_harvest_date: date
    season: Literal['Maha','Yala'] | None=None
    @field_validator('region')
    @classmethod
    def normalize(cls,value):return ' '.join(value.split()).casefold()
    @model_validator(mode='after')
    def dates(self):
        if self.expected_harvest_date<self.planting_date:raise ValueError('Harvest before planting')
        return self

class WorkflowAnalysis(BaseModel):
    model_config=ConfigDict(extra='forbid')
    plan_id: str
    season: Literal['Maha','Yala'] | None=None
    as_of: datetime | None=None

class WorkflowChoice(PlanningRequest):
    save: bool=False
