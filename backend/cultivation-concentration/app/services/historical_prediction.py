"""District-season proxy forecasting; never measures farmer-plan overlap."""
import math
from datetime import datetime,date,timezone

FEATURES=('Prior_History_Count','Historical_Mean_Land_Acres','Historical_Mean_Production_kg',
          'Historical_Mean_Yield_kg_per_Acre','District','Crop','Season','Target_Year')
LABEL_DEFINITION='official_equal_weight_cumulative_ratios_0.75_1.25_v1'

def unavailable(reason):
    return dict(status='insufficient_evidence',risk_level=None,scope='historical_district_crop_season_proxy',
        reason=reason,label_definition=LABEL_DEFINITION,
        interpretation='Operational historical concentration category, not real-time overlap, oversupply or market loss')

class HistoricalPredictor:
    """Trusted server-side bundle and availability manifest, never farmer input.

    Each observation must carry verified lineage and actual availability evidence.
    Missing latest-year coverage invalidates inference instead of using stale means.
    """
    def __init__(self,model,observations,model_name,model_available_at,trained_through,coverage_through):
        self.model=model;self.observations=observations;self.model_name=model_name
        self.model_available_at=model_available_at;self.trained_through=trained_through
        self.coverage_through=coverage_through

    def predict(self,district,crop,season,target_year,cutoff):
        if district not in ('Matara','Hambantota') or crop not in ('Bandakka','Brinjal','Pumpkin','Corn','Mung Beans','Chillies') or season not in ('Maha','Yala'):
            return unavailable('Unsupported district/crop/season combination')
        if cutoff.tzinfo is None or self.model_available_at.tzinfo is None or self.model_available_at>cutoff:
            return unavailable('Model was not available at the prediction cutoff')
        if target_year<=self.trained_through or self.coverage_through<target_year-1:
            return unavailable('Target is not out-of-training or preceding-year coverage is incomplete')
        history=[r for r in self.observations if (r['district'],r['crop'],r['season'])==(district,crop,season) and r['year']<target_year]
        if not history or max(r['year'] for r in history)!=target_year-1:
            return unavailable('No complete latest prior-year group baseline')
        if len({r['year'] for r in history})!=len(history):return unavailable('Duplicate historical keys')
        for r in history:
            available=r.get('available_at')
            if not r.get('provenance_verified') or not r.get('evidence_reference') or not isinstance(available,datetime) or available.tzinfo is None or available>cutoff:
                return unavailable('Historical lineage or actual availability is unverified at cutoff')
            if not all(math.isfinite(r[k]) and r[k]>=0 for k in ('land_acres','production_kg')) or r['land_acres']==0:
                return unavailable('Invalid historical measurement or undefined yield')
        import pandas as pd
        n=len(history)
        features=dict(Prior_History_Count=n,Historical_Mean_Land_Acres=sum(r['land_acres'] for r in history)/n,
            Historical_Mean_Production_kg=sum(r['production_kg'] for r in history)/n,
            Historical_Mean_Yield_kg_per_Acre=sum(r['production_kg']/r['land_acres'] for r in history)/n,
            District=district,Crop=crop,Season=season,Target_Year=target_year)
        predicted=int(self.model.predict(pd.DataFrame([features],columns=FEATURES))[0])
        if predicted not in (0,1,2):return unavailable('Model label encoding mismatch')
        return dict(status='historical_proxy_prediction',risk_level=('Low','Medium','High')[predicted],
            model=self.model_name,label_definition=LABEL_DEFINITION,target_year=target_year,
            scope='district_crop_season_not_region_or_harvest_window',
            interpretation='Proxy-category forecast; not independently verified oversupply, market loss or current farmer overlap')

def predict_context(predictor,owned,season,cutoff):
    if predictor is None:return unavailable('No approved model/availability bundle configured')
    if season is None:return unavailable('Season required for historical proxy inference')
    # Calendar planting year is not automatically a verified Maha/Yala statistical year.
    mapper=getattr(predictor,'season_year_mapper',None)
    if mapper is None:return unavailable('Verified planting-to-statistical-season-year mapping missing')
    try:
        planting=date.fromisoformat(owned['planting_date'])
        if cutoff.tzinfo is None or cutoff>datetime.now(timezone.utc) or cutoff.date()>=planting:
            return unavailable('Prediction cutoff must be aware, no later than now and before planting day')
        mapping=getattr(predictor,'season_year_mapping_evidence',{})
        available=mapping.get('available_at')
        if (mapping.get('verified') is not True or not mapping.get('reference') or
            not isinstance(available,datetime) or available.tzinfo is None or available>cutoff):
            return unavailable('Season/year mapping evidence unavailable or unverified at cutoff')
        target=mapper(owned,season)
        if target is None:return unavailable('Season/year mapping unavailable for this plan')
        if type(target) is not int:return unavailable('Season/year mapping returned invalid statistical year')
        return predictor.predict(owned['district'],owned['crop'],season,target,cutoff)
    except (ValueError,TypeError,KeyError,ArithmeticError):
        return unavailable('Historical model or availability bundle failed validation')
