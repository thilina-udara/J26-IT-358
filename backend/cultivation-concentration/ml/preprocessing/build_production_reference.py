"""Offline expected-production references. Never activates classification gates."""
import argparse
import csv
import hashlib
import json
import io
import math
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
import numpy as np

VERSION='district_expected_production_reference_v1'
REQUIRED=('Record_ID','District','Crop','Year','Season','Planting_Date','Expected_Harvest_Date',
          'Land_Size_Acres','Expected_Production_kg')
CROPS={'Bandakka','Brinjal','Pumpkin','Corn','Mung Beans','Chillies'}

def load_development(path):
    """Read Year for routing; excluded fields are never accessed/validated/hashed."""
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if not set(REQUIRED)<=set(reader.fieldnames or []):raise ValueError('Missing required columns')
        selected=[];excluded=0
        for row in reader:
            year=int(row['Year'])
            if not 2020<=year<=2023:
                excluded+=1;continue
            selected.append(row)
    return selected,excluded

def normalize(rows,reference_end_year=2023):
    unique={};duplicates=0
    for raw in rows:
        year=int(raw['Year'])
        if not 2020<=year<=reference_end_year:raise ValueError('Excluded cohort passed to builder')
        if raw['District'] not in {'Matara','Hambantota'} or raw['Crop'] not in CROPS or raw['Season'] not in {'Maha','Yala'}:
            raise ValueError('Unsupported district/crop/season')
        planting=datetime.strptime(raw['Planting_Date'],'%m/%d/%Y').date()
        harvest=datetime.strptime(raw['Expected_Harvest_Date'],'%m/%d/%Y').date()
        area=float(raw['Land_Size_Acres']);production=float(raw['Expected_Production_kg'])
        if harvest<planting or not math.isfinite(area) or area<=0 or not math.isfinite(production) or production<0:
            raise ValueError('Invalid measurement/date')
        identity=raw['Record_ID'].strip()
        if not identity:raise ValueError('Missing plan identity')
        row=dict(plan_id=identity,district=raw['District'],crop=raw['Crop'],year=year,season=raw['Season'],
            planting_date=planting.isoformat(),harvest_date=harvest.isoformat(),acres=area,expected_kg=production)
        if identity in unique:
            if unique[identity]!=row:raise ValueError('Conflicting duplicated plan identity')
            duplicates+=1
        else:unique[identity]=row
    if not unique:raise ValueError('Empty permitted cohort')
    return sorted(unique.values(),key=lambda r:(r['district'],r['crop'],r['season'],r['year'],r['harvest_date'],r['plan_id'])),duplicates

def quantiles(values):
    numbers=np.percentile(values,[25,33,50,67,75,90],method='linear')
    return dict(zip(('P25','P33','median','P67','P75','P90'),map(float,numbers)))

def build(rows,reference_end_year=2023):
    if reference_end_year not in (2023,2024):raise ValueError('Unsupported reference end year')
    plans,duplicates=normalize(rows,reference_end_year)
    windows=[];distributions=[]
    for scope,last_year in [('frozen_reference_2020_2021',2021),(f'descriptive_development_2020_{reference_end_year}',reference_end_year)]:
        groups=defaultdict(list)
        for p in plans:
            if p['year']<=last_year:groups[(p['district'],p['crop'],p['season'],p['year'])].append(p)
        for half in (7,14,21):
            scoped=[]
            for (district,crop,season,year),group in sorted(groups.items()):
                for anchor in sorted({p['harvest_date'] for p in group}):
                    date=datetime.fromisoformat(anchor).date()
                    members=[p for p in group if abs((datetime.fromisoformat(p['harvest_date']).date()-date).days)<=half]
                    item=dict(scope=scope,half_window_days=half,district=district,crop=crop,season=season,recorded_year=year,
                        harvest_anchor=anchor,window_start=(date-timedelta(days=half)).isoformat(),window_end=(date+timedelta(days=half)).isoformat(),
                        plan_count=len(members),acres=math.fsum(p['acres'] for p in members),expected_kg=math.fsum(p['expected_kg'] for p in members))
                    windows.append(item);scoped.append(item)
            for district,crop,season in sorted({key[:3] for key in groups}):
                for year in [None,*range(2020,last_year+1)]:
                    sample=[w for w in scoped if (w['district'],w['crop'],w['season'])==(district,crop,season) and (year is None or w['recorded_year']==year)]
                    if not sample:continue
                    members=[p for key,group in groups.items() if key[:3]==(district,crop,season) and (year is None or key[3]==year) for p in group]
                    distributions.append(dict(scope=scope,half_window_days=half,district=district,crop=crop,season=season,recorded_year=year,
                        plan_sample_size=len(members),anchor_sample_size=len(sample),independent_sample_size=None,
                        distributions={metric:quantiles([w[metric] for w in sample]) for metric in ('plan_count','acres','expected_kg')}))
    digest=hashlib.sha256(json.dumps(plans,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(version=VERSION if reference_end_year==2023 else 'district_expected_production_reference_backtest_2025_v1',development_cohort_sha256=digest,permitted_years=list(range(2020,reference_end_year+1)),
        unique_plan_count=len(plans),duplicate_identity_rows_collapsed=duplicates,
        provenance=dict(source='ASC reported by dataset owner',row_meaning='one cultivation plan reported by owner',
            independently_verified=False,production_semantics='recorded expected/planned kg, not observed actual harvest',
            publication_dates=None,availability_dates=None),
        method=dict(date_format='%m/%d/%Y',percentile_method='linear',
            grouping='district/crop/recorded-season/recorded-year; unique harvest anchors',
            cross_season_year_members=False,overlapping_anchors_independent=False,scope='research_only_no_risk_labels',
            denominator='comparable harvest-window kg; never annual production'),
        windows=windows,reference_distributions=distributions)

def save(bundle,output_dir):
    """Exclusive deterministic file creation; safe identical rerun, never overwrite."""
    encoded=json.dumps(bundle,sort_keys=True,indent=2,allow_nan=False)+'\n'
    digest=hashlib.sha256(encoded.encode()).hexdigest()
    path=Path(output_dir)/f'{bundle["version"]}_{digest[:16]}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(encoded)
        status='created'
    except FileExistsError:
        if path.read_text(encoding='utf-8')!=encoded:raise ValueError('Existing artifact differs; preserved')
        status='identical_existing_preserved'
    csv_stream=io.StringIO(newline='')
    fields=['scope','half_window_days','district','crop','season','recorded_year','plan_sample_size','anchor_sample_size']
    fields += [f'{metric}_{stat}' for metric in ('plan_count','acres','expected_kg') for stat in ('P25','P33','median','P67','P75','P90')]
    writer=csv.DictWriter(csv_stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for cell in bundle['reference_distributions']:
        value={field:cell[field] for field in fields[:8]}
        value.update({f'{metric}_{stat}':number for metric,stats in cell['distributions'].items() for stat,number in stats.items()})
        writer.writerow(value)
    csv_path=path.with_name(path.stem+'_distributions.csv');csv_text=csv_stream.getvalue()
    try:
        with csv_path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(csv_text)
    except FileExistsError:
        if csv_path.read_text(encoding='utf-8')!=csv_text:raise ValueError('Existing CSV differs; preserved')
    return path,status

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[2]/'data/research/production_reference/v1')
    args=parser.parse_args()
    rows,excluded=load_development(args.input)
    bundle=build(rows)
    bundle['source_file']=str(args.input.resolve())
    bundle['excluded_rows_routed_by_year_only']=excluded
    path,status=save(bundle,args.output_dir)
    print(json.dumps(dict(artifact=str(path),status=status,plans=bundle['unique_plan_count'],
        windows=len(bundle['windows']),distribution_cells=len(bundle['reference_distributions']),excluded=excluded)))

if __name__=='__main__':main()
