"""Explicit approval overlay gates source-checked v1.1 claims; no auto activation."""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from fastapi import HTTPException
from app.schemas.personalized_planning import ClaimApproval
from app.schemas.cultivation_plan import PlanInput
from app.schemas.alternatives import AlternativeRequest
from app.services.alternatives import compare_alternatives

DATA=Path(__file__).resolve().parents[2]/'data/guidelines/v1.1'
HECTARE_ACRES=2.4710538147


def generate(repository,request,farmer,approvals,evidence,guideline_dir=DATA):
    current=repository.read(request.plan_id,farmer)['plan']
    if current.status!='active':raise HTTPException(409,'Cancelled plans cannot be planned')
    now=datetime.now(timezone.utc);cutoff=request.as_of or now
    if cutoff.tzinfo is None or cutoff>now:raise HTTPException(422,'Invalid analysis cutoff')
    cutoff=cutoff.astimezone(timezone.utc)
    if current.updated_at>cutoff:raise HTTPException(409,'Current owned revision was not available at cutoff')
    if request.planting_date<=cutoff.date():raise HTTPException(422,'Planting must be after cutoff')
    harvest=request.expected_harvest_date or current.expected_harvest_date
    if harvest<request.planting_date:raise HTTPException(422,'Harvest before planting')
    crop='Bandakka' if request.final_crop=='Bandakka' else request.final_crop
    if crop!=current.crop:
        comparison=compare_alternatives(repository,AlternativeRequest(selected_crop=current.crop,district=request.district,
            region=request.region,land_size_acres=request.land_size_acres,planting_date=request.planting_date,
            expected_harvest_date=harvest,as_of=cutoff,replacing_plan_id=current.plan_id),farmer,evidence)
        if crop not in {a['crop'] for a in comparison['alternatives']}:
            raise HTTPException(409,'Alternative is not Phase 4 eligible under current evidence/coverage')
    entries=json.loads((Path(guideline_dir)/'verified_entries.json').read_text(encoding='utf-8'))['entries']
    approved=[ClaimApproval.model_validate(a) for a in approvals]
    warnings=['No complete-plan claim: soil/water suitability, evidence coverage and stage observations require review.',
              'No Low/Medium/High risk or guaranteed yield/oversupply reduction is inferred.']
    activities=[]
    anchors={'direct_sowing':request.planting_date if request.planting_method=='direct_sowing' else None,
             'transplanting':request.planting_date if request.planting_method=='transplanting' else None,
             'nursery_sowing':request.nursery_sowing_date,'emergence':request.emergence_date,'flowering':request.flowering_date}
    for entry in entries:
        if entry['crop_name']!=crop or entry['verification_status']!='source_checked' or not entry['source_url']:
            continue
        approval=next((a for a in approved if a.entry_id==entry['entry_id'] and a.claim_verified
            and a.available_at<=cutoff and a.approved_at<=cutoff
            and (a.district,a.region.strip().casefold(),a.season)==(request.district,request.region,request.season)
            and a.variety==request.variety and a.planting_method==request.planting_method
            and (crop!='Corn' or (request.corn_product is not None and a.corn_product==request.corn_product))),None)
        if approval is None:continue
        if entry['district_applicability'] is not None and request.district not in entry['district_applicability']:continue
        if entry['season'] is not None and request.season not in entry['season']:continue
        if entry['variety'] is not None and entry['variety']!=request.variety:
            warnings.append(f"{entry['entry_id']}: exact variety/method mapping missing")
            continue
        # No implicit generic grain instruction may govern baby/sweet corn.
        if crop=='Corn' and request.corn_product!='field_grain':
            warnings.append('v1.1 corn claims lack explicit baby/sweet applicability; withheld')
            continue
        if entry['guideline_category']=='yield':continue
        activity=dict(activity_name=entry['activity_name'],category=entry['guideline_category'],notes=entry['notes'],
            source_url=entry['source_url'],guideline_version='1.1.0',verification_status='explicitly_verified_for_planning',
            approval_evidence=approval.evidence_reference,entry_id=entry['entry_id'],
            applicability=dict(variety=request.variety,district=request.district,region=request.region,season=request.season),
            timing_reference=entry['timing_reference'],date_windows=[],quantity=None)
        offset=entry['days_offset'];anchor=anchors.get(entry['timing_reference'])
        if offset and anchor:
            start=anchor+timedelta(days=offset['min']);end=anchor+timedelta(days=offset['max'])
            interval=entry['repeat_interval_days'];count=entry['max_occurrences'] or 1
            # First-harvest range vs bounded overall harvesting window are distinct.
            if interval and entry['guideline_category']=='harvest' and crop=='Bandakka':
                windows=[(d,d) for d in (start+timedelta(days=i*interval) for i in range(count)) if d<=end]
            elif interval and entry['guideline_category']=='harvest':
                windows=[(start+timedelta(days=i*interval),end+timedelta(days=i*interval)) for i in range(count)]
            else:windows=[(start,end)]
            activity['date_windows']=[dict(earliest=a.isoformat(),latest=b.isoformat()) for a,b in windows]
            if any(a<cutoff.date() for a,b in windows):
                warnings.append(f"{entry['entry_id']}: scheduled activity precedes analysis cutoff; withheld")
                continue
        else:
            warnings.append(f"{entry['entry_id']}: timing anchor/offset unavailable; undated guidance only")
        rate=entry['rate_per_hectare'];unit=entry['unit']
        if rate and unit in ('kg/ha','g/ha','t/ha','kg product/ha'):
            scale=request.land_size_acres/HECTARE_ACRES
            activity['quantity']=dict(min=rate['min']*scale,max=rate['max']*scale,
                unit={'kg/ha':'kg','g/ha':'g','t/ha':'t','kg product/ha':'kg product'}[unit],rate_per_hectare=rate)
        elif rate:warnings.append(f"{entry['entry_id']}: incompatible quantity unit withheld")
        activities.append(activity)
    activities.sort(key=lambda a:a['date_windows'][0]['earliest'] if a['date_windows'] else '9999')
    if not activities:warnings.append('No explicitly verified applicable claims; all v1.1 claims remain inactive without an approval overlay.')
    if request.planting_method is None:warnings.append('Specify direct sowing versus transplanting; dates are not interchangeable.')
    missing=sorted(set(('land_preparation','establishment','fertilizer','management','harvest'))-{a['category'] for a in activities})
    return dict(status='partial_plan',plan_id=current.plan_id,final_crop=crop,as_of=cutoff.isoformat(),
                request=request.model_dump(mode='json'),expected_harvest_date=harvest.isoformat(),
                activities=activities,warnings=warnings,missing_categories=missing,
                based_on_updated_at=current.updated_at.isoformat())


def save_choice(repository,request,farmer,approvals,evidence,guideline_dir=DATA):
    if request.as_of is not None:raise HTTPException(422,'Saving requires current evidence; omit as_of')
    report=generate(repository,request,farmer,approvals,evidence,guideline_dir)
    value=PlanInput(farmer_id=farmer,district=request.district,region=request.region,crop=request.final_crop,
        land_size_acres=request.land_size_acres,planting_date=request.planting_date,
        expected_harvest_date=report['expected_harvest_date'],status='active')
    repository.save(value,farmer,request.plan_id,datetime.fromisoformat(report['based_on_updated_at']),report)
    return retrieve(repository,request.plan_id,farmer)


def retrieve(repository,plan_id,farmer):
    with repository.connection() as db:
        db.execute('BEGIN')
        current=repository.get(db,plan_id,farmer)
        rows=db.execute('SELECT revision_id,saved_at,payload FROM personalized_plan_versions WHERE plan_id=? AND farmer_id=? ORDER BY revision_id',
                        (plan_id,farmer)).fetchall()
        if not rows:raise HTTPException(404,'No personalized plan saved')
        latest=json.loads(rows[-1]['payload'])
        return dict(personalized_plan=latest,revision_id=rows[-1]['revision_id'],
            revisions=[dict(revision_id=r['revision_id'],saved_at=r['saved_at']) for r in rows],
            stale=current.updated_at.isoformat()!=latest['cultivation_updated_at'] or current.status!='active')
