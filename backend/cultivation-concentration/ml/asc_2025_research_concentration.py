"""Offline retrospective acreage categories; not production risk or ground truth."""
import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import date,timedelta
from pathlib import Path

import numpy as np

from ml.asc_2025_actual_evaluation import load_authorized,LABELS
from ml.asc_2025_backtest import overlap_cohort
from ml.preprocessing.build_production_reference import build,normalize,save

SCOPE='descriptive_development_2020_2023'
LIMITATIONS=[
    'HINDSIGHT: original submission/publication timestamps are unavailable; pre-planting availability is unverified.',
    'Assume submission immediately before planting; same-date peers excluded; activity lasts through expected harvest.',
    'Current progressive submissions are compared with completed historical season/year windows, not matched registration lead-time snapshots.',
    'Recorded season matching does not verify agricultural season-year mapping.',
    'Owner-reported ASC provenance and representative collection coverage are independently unverified.',
    'Overlapping reference anchors are correlated, not independent samples; plan IDs are not unique farmer identities.',
    'Categories describe relative recorded planned acreage, not observed harvest, market risk or recommendation approval.'
]


def classify(acres,district,crop,season,reference):
    result=dict(research_concentration_category='insufficient_evidence',validation_status='experimental',
        current_overlap_acres=acres,historical_p33_acres=None,historical_p67_acres=None,
        reference_sample_size=None,district=district,crop=crop,season=season,
        limitations=list(LIMITATIONS),reasons=[])
    try:
        if not math.isfinite(acres) or acres<=0:raise ValueError('Invalid current acreage')
        if reference['permitted_years']!=[2020,2021,2022,2023]:raise ValueError('Reference cohort mismatch')
        method=reference['method']
        if method['percentile_method']!='linear' or method['cross_season_year_members'] is not False or method['grouping']!='district/crop/recorded-season/recorded-year; unique harvest anchors':
            raise ValueError('Reference method mismatch')
        match=dict(scope=SCOPE,half_window_days=14,district=district,crop=crop,season=season)
        cells=[c for c in reference['reference_distributions'] if all(c[k]==v for k,v in match.items()) and c['recorded_year'] is None]
        if len(cells)!=1:raise ValueError('Missing or ambiguous matching reference cell')
        cell=cells[0]
        windows=[w for w in reference['windows'] if all(w[k]==v for k,v in match.items())]
        if not windows or len(windows)!=cell['anchor_sample_size'] or cell['plan_sample_size']<=0:
            raise ValueError('Empty or inconsistent reference sample')
        seen=set()
        for w in windows:
            key=(w['recorded_year'],w['harvest_anchor'])
            if key in seen:raise ValueError('Duplicated reference anchor')
            seen.add(key)
            anchor=date.fromisoformat(w['harvest_anchor'])
            if anchor>=date(2025,1,1):raise ValueError('Historical harvest anchor is not before evaluation year')
            if w['recorded_year'] not in (2020,2021,2022,2023) or w['acres']<=0 or not math.isfinite(w['acres']):
                raise ValueError('Invalid historical observation')
            if date.fromisoformat(w['window_start'])!=anchor-timedelta(days=14) or date.fromisoformat(w['window_end'])!=anchor+timedelta(days=14):
                raise ValueError('Harvest-window definition mismatch')
        lower,upper=map(float,np.percentile([w['acres'] for w in windows],[33,67],method='linear'))
        stats=cell['distributions']['acres']
        if not math.isclose(lower,stats['P33']) or not math.isclose(upper,stats['P67']):
            raise ValueError('Reference quantiles do not match windows')
        result.update(historical_p33_acres=lower,historical_p67_acres=upper,reference_sample_size=len(windows),
            reference_plan_sample_size=cell['plan_sample_size'])
        if lower>=upper:raise ValueError('Degenerate reference boundaries cannot distinguish categories')
        # Preserve inclusive boundaries despite percentile floating-point roundoff.
        at_lower=math.isclose(acres,lower,rel_tol=1e-12,abs_tol=1e-12)
        at_upper=math.isclose(acres,upper,rel_tol=1e-12,abs_tol=1e-12)
        result['research_concentration_category']='Low' if acres<lower and not at_lower else 'High' if acres>upper and not at_upper else 'Medium'
    except (KeyError,TypeError,ValueError) as error:
        result['reasons'].append(str(error))
    return result


def analyze(history,current):
    if any(not 2020<=int(r['Year'])<=2023 for r in history):raise ValueError('Protected/reference cohort rejected')
    if any(int(r['Year'])!=2025 for r in current):raise ValueError('Only authorized 2025 replay allowed')
    reference=build(history)
    plans,_=normalize(current,reference_end_year=2025)
    plans.sort(key=lambda p:(p['planting_date'],p['plan_id']))
    seen=[];rows=[]
    for p in plans:
        own=dict(p,expected_harvest_date=p['harvest_date'])
        peers=[q for q in seen if q['planting_date']<p['planting_date'] and q['harvest_date']>=p['planting_date']]
        cohort=overlap_cohort(peers,own,p['season'])
        seen.append(own)
        result=classify(math.fsum(q['acres'] for q in cohort),p['district'],p['crop'],p['season'],reference)
        result.update(case_index=len(rows)+1,planting_date=p['planting_date'],expected_harvest_date=p['harvest_date'],
            overlapping_plan_count=len(cohort),supporting_recorded_expected_production_kg=math.fsum(q['expected_kg'] for q in cohort))
        rows.append(result)
    def counts(sample):
        values=Counter(r['research_concentration_category'] for r in sample)
        return dict(total=len(sample),**{label:values[label] for label in LABELS})
    return dict(mode='research_concentration_category',version='asc_2025_research_acreage_v1',
        validation_status='experimental',reference=reference,results=rows,summary=counts(rows),
        by_district={d:counts([r for r in rows if r['district']==d]) for d in ('Matara','Hambantota')},
        by_district_crop={d:{c:counts([r for r in rows if (r['district'],r['crop'])==(d,c)])
            for c in sorted({r['crop'] for r in rows})} for d in ('Matara','Hambantota')})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--authorize-asc-2025',action='store_true')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    history,current,excluded=load_authorized(args.input,authorize_2025=args.authorize_asc_2025)
    result=analyze(history,current)
    result.update(excluded_rows_routed_by_year_only=excluded,source='ASC as reported by owner; unverified')
    reference_path,_=save(result['reference'],args.output_dir/'references')
    result['reference_artifact']=reference_path.name
    encoded=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
    digest=hashlib.sha256(encoded.encode()).hexdigest()[:16]
    path=args.output_dir/f'asc_2025_research_acreage_{digest}.json'
    try:
        with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(encoded)
    except FileExistsError:
        if path.read_text(encoding='utf-8')!=encoded:raise ValueError('Existing output differs; preserved')
    print(json.dumps(dict(artifact=str(path),summary=result['summary'],by_district=result['by_district'],by_district_crop=result['by_district_crop'])))


if __name__=='__main__':main()
