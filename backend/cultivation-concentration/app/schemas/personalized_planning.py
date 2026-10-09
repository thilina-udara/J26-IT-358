from datetime import date,datetime
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from app.schemas.cultivation_plan import District


class PlanningRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    plan_id: str
    final_crop: Literal['Bandakka','Brinjal','Pumpkin','Corn','Mung Beans','Chillies']
    district: District
    region: str=Field(min_length=1,max_length=100)
    land_size_acres: float=Field(gt=0,allow_inf_nan=False)
    planting_date: date
    season: Literal['Maha','Yala']
    variety: str | None=None
    planting_method: Literal['direct_sowing','transplanting'] | None=None
    corn_product: Literal['field_grain','sweet','baby'] | None=None
    nursery_sowing_date: date | None=None
    emergence_date: date | None=None
    flowering_date: date | None=None
    expected_harvest_date: date | None=None
    as_of: datetime | None=None

    @field_validator('region')
    @classmethod
    def normalize(cls,value):return ' '.join(value.split()).casefold()

    @model_validator(mode='after')
    def dates(self):
        if self.expected_harvest_date and self.expected_harvest_date<self.planting_date:
            raise ValueError('Harvest before planting')
        if self.nursery_sowing_date and self.nursery_sowing_date>self.planting_date:
            raise ValueError('Nursery sowing after field establishment')
        for value in (self.emergence_date,self.flowering_date):
            if value and value<self.planting_date:raise ValueError('Field stage before planting')
        return self


class ClaimApproval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    entry_id: str
    dataset_version: Literal['1.1.0']='1.1.0'
    claim_verified: bool=False
    approved_by: str=Field(min_length=1)
    evidence_reference: str=Field(min_length=1)
    available_at: datetime
    approved_at: datetime
    district: District
    region: str
    season: Literal['Maha','Yala']
    variety: str | None=None
    planting_method: Literal['direct_sowing','transplanting']
    corn_product: Literal['field_grain','sweet','baby'] | None=None

    @model_validator(mode='after')
    def timezone(self):
        if self.available_at.tzinfo is None or self.approved_at.tzinfo is None:
            raise ValueError('Approval timestamps require timezones')
        return self
