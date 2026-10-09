"""Experimental district-window supply proxy. No risk gate promotion."""
from datetime import datetime,date
import math
import numpy as np

COLLECTIVE=('expected_total_production_kg','historical_reference_production_kg','production_ratio',
            'overlapping_plan_count','overlapping_acres')

def evaluate(plans,owned,season,cutoff,registry):
    # Replace the owned ID before inserting the scenario once, including alternatives.
    records={p['plan_id']:p for p in plans if p['plan_id']!=owned['plan_id']}
    records[owned['plan_id']]=owned
    harvest=date.fromisoformat(owned['expected_harvest_date'])
    cohort=[p for p in records.values() if (p['district'],p['crop'])==(owned['district'],owned['crop'])
        and abs((date.fromisoformat(p['expected_harvest_date'])-harvest).days)<=14]
    result=dict(experimental_risk_level=None,validation_status='insufficient_evidence',
        **{k:None for k in COLLECTIVE},new_farmer_production_kg=None,
        explanation='Experimental expected harvest supply concentration, not market demand, price or loss prediction',reasons=[])
    reasons=result['reasons']
    entry=next((e for e in registry.evidence if (e.district,e.crop,e.season)==(owned['district'],owned['crop'],season)
        and e.verified and e.available_at<=cutoff and e.verified_at<=cutoff
        and e.valid_from<=date.fromisoformat(owned['planting_date'])<=harvest<=e.valid_to
        and e.historical_observation_end<cutoff.date() and e.applicable_without_variety_or_product
        and e.comparable_coverage_verified and e.quantile_method_approved_for_experiment),None)
    if entry is None:reasons.append('Verified yield and comparable production-window reference unavailable at cutoff')
    for plan in cohort:
        if plan['plan_id']==owned['plan_id']:continue
        mapped=any(a.plan_id==plan['plan_id'] and a.updated_at==datetime.fromisoformat(plan['updated_at'])
            and a.season==season and a.verified and a.available_at<=cutoff for a in registry.season_assignments)
        if not mapped:
            reasons.append('Overlapping plan season/revision compatibility unverified');break
    if len({p['farmer_id'] for p in cohort})<3:reasons.append('Small-group privacy or insufficient farmer coverage')
    if reasons:return result
    if any(not entry.valid_from<=date.fromisoformat(p['planting_date'])<=date.fromisoformat(p['expected_harvest_date'])<=entry.valid_to for p in cohort):
        reasons.append('Yield applicability does not cover all overlapping plans');return result
    acreage=math.fsum(p['land_size_acres'] for p in cohort)
    total=acreage*entry.yield_kg_per_acre
    lower,median,upper=np.percentile(entry.reference_window_production_kg,[33,50,67],method='linear')
    if lower==upper:reasons.append('Reference percentiles cannot distinguish categories');return result
    result.update(experimental_risk_level='Low' if total<lower else 'High' if total>upper else 'Medium',
        validation_status='experimental_operational_proxy_not_validated',expected_total_production_kg=total,
        historical_reference_production_kg=float(median),production_ratio=total/median,
        overlapping_plan_count=len(cohort),overlapping_acres=acreage,
        new_farmer_production_kg=owned['land_size_acres']*entry.yield_kg_per_acre,
        evidence_reference=entry.reference,reference_definition=entry.reference_definition,
        explanation='All overlapping acres estimated once with applicable historical kg/acre; compare against approved experimental district/crop/season 29-day production P33/P67. Median reference defines ratio, not a separate classification threshold.')
    return result

def farmer_response(result):
    # Exact collective supply/ratio can be differenced via owner acreage edits.
    return dict(result,**{k:None for k in COLLECTIVE},privacy_status='collective_metrics_withheld_from_farmer')

def alternatives(plans,owned,season,cutoff,registry,suitability_registry,current):
    from app.services.alternatives import applicable
    from app.schemas.alternatives import AlternativeRequest
    result=[]
    if current['experimental_risk_level']!='High':return result
    request=AlternativeRequest(selected_crop=owned['crop'],district=owned['district'],region=owned['region'],
        land_size_acres=owned['land_size_acres'],planting_date=owned['planting_date'],expected_harvest_date=owned['expected_harvest_date'])
    duration=(request.expected_harvest_date-request.planting_date).days
    for crop in ('Bandakka','Brinjal','Pumpkin','Corn','Mung Beans','Chillies'):
        if crop==owned['crop']:continue
        guideline=next((e for e in suitability_registry.suitability if applicable(e,request,crop,cutoff)
            and e.applicable_without_additional_inputs and e.valid_from<=request.planting_date<=request.expected_harvest_date<=e.valid_to
            and e.min_land_acres<=request.land_size_acres<=e.max_land_acres and e.min_harvest_days<=duration<=e.max_harvest_days),None)
        if guideline is None:continue
        candidate=evaluate(plans,dict(owned,crop=crop),season,cutoff,registry)
        if candidate['experimental_risk_level'] in ('Low','Medium'):
            result.append(dict(crop=crop,assessment=farmer_response(candidate),suitability_reference=guideline.source_reference,
                status='experimental_candidate_not_approved_recommendation'))
    return sorted(result,key=lambda r:({'Low':0,'Medium':1}[r['assessment']['experimental_risk_level']],r['crop']))[:3]
