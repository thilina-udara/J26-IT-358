"""Fail-closed alternatives; no manufactured agronomic rules or risk levels."""
from datetime import datetime,timezone,timedelta,date
from typing import get_args
import math
from fastapi import HTTPException
from app.schemas.cultivation_plan import Crop
from app.services.plan_clustering import snapshot,MIN_FARMERS


def applicable(entry,request,crop,cutoff):
    return (entry.verified and entry.available_at<=cutoff and entry.verified_at<=cutoff
        and (entry.district,entry.region,entry.crop)==(request.district,request.region,crop))


def compare_alternatives(repository,request,farmer,registry):
    now=datetime.now(timezone.utc);cutoff=request.as_of or now
    if cutoff.tzinfo is None or cutoff>now:
        raise HTTPException(422,'as_of must be timezone-aware and no later than now')
    cutoff=cutoff.astimezone(timezone.utc)
    if request.planting_date<=cutoff.date():
        raise HTTPException(422,'Planting must be strictly after the analysis cutoff')
    plans=snapshot(repository,cutoff)
    if request.replacing_plan_id:
        owned=next((p for p in plans if p['plan_id']==request.replacing_plan_id and p['farmer_id']==farmer),None)
        if owned is None:
            raise HTTPException(404,'Active available replacement plan not found')
        plans=[p for p in plans if p['plan_id']!=request.replacing_plan_id]
    start=request.expected_harvest_date-timedelta(days=14)
    end=request.expected_harvest_date+timedelta(days=14)

    def context(crop):
        cohort=[p for p in plans if (p['district'],p['region'],p['crop'])==(request.district,request.region,crop)]
        window=[p for p in cohort if start<=date.fromisoformat(p['expected_harvest_date'])<=end]
        # Count genuine registered farmers before adding the hypothetical scenario.
        if len({p['farmer_id'] for p in window})<MIN_FARMERS:
            return dict(status='suppressed_or_insufficient')
        acres=math.fsum(p['land_size_acres'] for p in window)
        total=math.fsum(p['land_size_acres'] for p in cohort)
        return dict(status='available',planned_acreage=acres,overlapping_farmer_count=len({p['farmer_id'] for p in window}),
            scenario_inclusive_acreage=acres+request.land_size_acres,
            scenario_inclusive_farmer_count=len({p['farmer_id'] for p in window}|{farmer}),
            harvest_overlap_intensity=(acres+request.land_size_acres)/(total+request.land_size_acres))

    def coverage(crop):
        return next((e for e in registry.coverage if applicable(e,request,crop,cutoff)
            and e.comparable_registration_scope and e.valid_from<=start and e.valid_to>=end),None)

    selected=context(request.selected_crop);selected_coverage=coverage(request.selected_crop)
    alternatives=[];comparisons=[]
    for crop in sorted(set(get_args(Crop))-{request.selected_crop}):
        values=context(crop);reasons=[]
        crop_coverage=coverage(crop)
        duration=(request.expected_harvest_date-request.planting_date).days
        guideline=next((e for e in registry.suitability if applicable(e,request,crop,cutoff)
            and e.applicable_without_additional_inputs
            and e.valid_from<=request.planting_date<=request.expected_harvest_date<=e.valid_to
            and e.min_land_acres<=request.land_size_acres<=e.max_land_acres
            and e.min_harvest_days<=duration<=e.max_harvest_days),None)
        if guideline is None:reasons.append('Verified applicable suitability guideline unavailable at cutoff')
        if crop_coverage is None or selected_coverage is None:reasons.append('Comparable crop/region/harvest-window coverage evidence unavailable at cutoff')
        elif crop_coverage.registration_scope_id!=selected_coverage.registration_scope_id:
            reasons.append('Coverage registry scopes differ across compared crops')
        if values['status']!='available' or selected['status']!='available':reasons.append('Small-group privacy or insufficient registered farmer coverage')
        entry=dict(crop=crop,status='insufficient_evidence' if reasons else 'comparison_available',
                   planned_concentration=values,missing_evidence=reasons,risk_level='unknown_unvalidated',
                   historical_context=None,
                   data_limitations=['No compatible historical regional/season/window baseline','Declared plans/harvest dates not independently verified',
                                    'Scenario is hypothetical and is not persisted; acreage is not actual supply',
                                    'Aggregate suppression is not differential privacy; repeated comparisons may permit inference'])
        if not reasons:
            lower=values['scenario_inclusive_acreage']<selected['scenario_inclusive_acreage']
            no_more_intense=values['harvest_overlap_intensity']<=selected['harvest_overlap_intensity']
            entry.update(lower_observed_planned_concentration=lower,
                suitability_evidence=dict(evidence_id=guideline.evidence_id,source_reference=guideline.source_reference,
                    applicability_statement=guideline.applicability_statement),
                coverage_evidence=[dict(evidence_id=e.evidence_id,source_reference=e.source_reference,statement=e.coverage_statement) for e in (selected_coverage,crop_coverage)],
                harvest_window_comparison=dict(start=start.isoformat(),end=end.isoformat(),selected=selected,alternative=values))
            if lower and no_more_intense:
                entry['status']='eligible_alternative'
                entry['recommendation_explanation']='Lower registered planned acreage in the same harvest window without a higher acreage overlap share; applicable suitability and comparable coverage attestations are available. Risk remains unvalidated.'
                alternatives.append(entry)
            else:
                entry['recommendation_explanation']='Suitability and coverage permit comparison, but lower acreage with no higher overlap share is not established.'
        comparisons.append(entry)
    return dict(status='alternatives_available' if alternatives else 'insufficient_evidence' if any(e['status']=='insufficient_evidence' for e in comparisons) else 'no_lower_concentration_alternative',
                as_of=cutoff.isoformat(),selected_crop=request.selected_crop,selected_concentration=selected,
                alternatives=alternatives,comparisons=comparisons,
                risk_level='unknown_unvalidated',interpretation='Conditional planned-concentration comparison, not demonstrated reduction in actual market oversupply.')
