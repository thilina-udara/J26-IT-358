"""Append-only assessments over existing authenticated, versioned registration storage."""
import hashlib,json,sqlite3
from datetime import datetime,timezone,timedelta,date
from uuid import uuid4
from fastapi import HTTPException
from pydantic import ValidationError
from app.schemas.prospective import Forecast
from app.services.plan_clustering import snapshot_versions

TABLES=('prospective_protocols','prospective_assessments','prospective_outcomes')

def now():return datetime.now(timezone.utc)
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(payload):return hashlib.sha256(payload.encode()).hexdigest()

def initialize(repository):
    with repository.connection() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS prospective_protocols(id TEXT PRIMARY KEY,payload TEXT NOT NULL,digest TEXT NOT NULL,recorded_at TEXT NOT NULL,actor TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS prospective_assessments(id TEXT PRIMARY KEY,owner TEXT NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL,recorded_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS prospective_outcomes(id TEXT PRIMARY KEY,payload TEXT NOT NULL,digest TEXT NOT NULL,recorded_at TEXT NOT NULL,actor TEXT NOT NULL);
        ''')
        for table in TABLES:
            for operation in ('UPDATE','DELETE'):
                db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'Immutable prospective record'); END")
            db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_replace BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Immutable prospective record'); END")

def read_verified(db,table,identity):
    if table not in TABLES:raise ValueError('Unsupported audit table')
    row=db.execute(f'SELECT * FROM {table} WHERE id=?',(identity,)).fetchone()
    if row is None:raise HTTPException(404,'Record not found')
    if digest(row['payload'])!=row['digest']:raise HTTPException(503,'Audit integrity check failed')
    return row,json.loads(row['payload'])

def register_protocol(repository,value,actor):
    initialize(repository);stamp=now().isoformat();payload=encoded(dict(value.model_dump(mode='json'),registered_at=stamp))
    try:
        with repository.connection() as db:db.execute('INSERT INTO prospective_protocols VALUES(?,?,?,?,?)',(value.protocol_id,payload,digest(payload),stamp,actor))
    except sqlite3.IntegrityError:raise HTTPException(409,'Protocol is immutable; use a new version')
    return json.loads(payload)

def assess(repository,identity,request,predictor=None):
    initialize(repository)
    with repository.connection() as db:
        # Same database transaction fixes the snapshot and persists output before any writer proceeds.
        db.execute('BEGIN IMMEDIATE');cutoff=now()
        if cutoff.tzinfo is None:raise HTTPException(503,'Server clock must be timezone-aware')
        repository.get(db,request.plan_id,identity)
        try:
            versions=snapshot_versions(repository,cutoff,db)
        except (TypeError, ValueError) as exc:
            raise HTTPException(503,'Invalid registration timestamp evidence') from exc
        own=next((e for e in versions if e['plan']['plan_id']==request.plan_id),None)
        if own is None:raise HTTPException(409,'Own plan not active and available before planting')
        plan=own['plan'];anchor=date.fromisoformat(plan['expected_harvest_date']);start=anchor-timedelta(days=14);end=anchor+timedelta(days=14)
        scoped=[e for e in versions if all(e['plan'][c]==plan[c] for c in ('district','region','crop')) and e['plan']['plan_id']!=plan['plan_id']]
        overlap=[e for e in scoped if start<=date.fromisoformat(e['plan']['expected_harvest_date'])<=end]
        def private_version(entry):
            p={k:v for k,v in entry['plan'].items() if k!='farmer_id'}
            timestamps=[datetime.fromisoformat(p['submitted_at']),datetime.fromisoformat(p['updated_at']),datetime.fromisoformat(entry['recorded_at'])]
            if any(t.tzinfo is None for t in timestamps) or not timestamps[0]<=timestamps[1]<=timestamps[2]<=cutoff:
                raise HTTPException(503,'Invalid plan version timestamp evidence')
            return dict(plan=p,version_id=entry['version_id'],recorded_at=entry['recorded_at'],payload_sha256=digest(encoded(entry['plan'])))
        protocol=None
        if request.protocol_id:
            _,protocol=read_verified(db,'prospective_protocols',request.protocol_id)
            if datetime.fromisoformat(protocol['registered_at'])>cutoff:raise HTTPException(409,'Protocol not available at cutoff')
        identifier=str(uuid4());payload={'schema_version':1,'assessment_id':identifier,'assessment_timestamp':cutoff.isoformat(),
            'cutoff':cutoff.isoformat(),'own_plan':private_version(own),'district':plan['district'],'crop':plan['crop'],
            'region':plan['region'],'expected_harvest_date':plan['expected_harvest_date'],
            'available_peer_plan_ids':[e['plan']['plan_id'] for e in scoped],
            'peer_versions':[private_version(e) for e in scoped],
            'known_concentration':{'kind':'registered_preplanting_intentions','category':None,'overlapping_peer_plan_ids':[e['plan']['plan_id'] for e in overlap],
                'overlap_acres_including_own':sum(e['plan']['land_size_acres'] for e in overlap)+plan['land_size_acres'],
                'window_start':start.isoformat(),'window_end':end.isoformat(),'districts_pooled':False,
                'coverage':'registered plans only; participation and intention accuracy unverified','season_filter':'unverified; plans have no season assignment'},
            'protocol':protocol,'outcome_due_at':(cutoff+timedelta(days=protocol['horizon_days'])).isoformat() if protocol else None}
        forecast=Forecast(status='unavailable',reason='No trusted prospective forecast provider/protocol configured')
        if predictor is not None and protocol is not None:
            # Provider gets an isolated copy; output is server-side, never client supplied.
            try:
                forecast=Forecast.model_validate(predictor(json.loads(encoded(payload))))
            except ValidationError as exc:
                raise HTTPException(503,'Invalid trusted forecast evidence') from exc
            if forecast.status=='experimental_forecast':
                if forecast.target_definition_version!=protocol['definition_version']:raise HTTPException(422,'Forecast target does not match frozen protocol')
                if any(a.available_at>cutoff for a in (forecast.model,forecast.historical_reference)):raise HTTPException(422,'Model/reference unavailable at cutoff')
        payload['experimental_forecast']=forecast.model_dump(mode='json');payload['historical_reference_version']=forecast.historical_reference.version if forecast.historical_reference else None
        payload['model_version']=forecast.model.version if forecast.model else None
        text=encoded(payload);db.execute('INSERT INTO prospective_assessments VALUES(?,?,?,?,?)',(identifier,identity,text,digest(text),cutoff.isoformat()))
    return farmer_assessment(payload)

def farmer_assessment(value):
    # Allow-list: never expose collective values, peer IDs/version hashes, or identities.
    return {'assessment_id':value['assessment_id'],'assessment_timestamp':value['assessment_timestamp'],
        'own_plan':value['own_plan']['plan'],'known_concentration':{'status':'collective_details_withheld','coverage':value['known_concentration']['coverage']},
        'experimental_forecast':{'status':value['experimental_forecast']['status'],'category':None,
            'reason':'Experimental outputs retained for restricted evaluation; no farmer risk claim'},
        'outcome_due_at':value['outcome_due_at']}

def get_assessment(repository,identity,identifier,restricted=False):
    initialize(repository)
    with repository.connection() as db:
        row,payload=read_verified(db,'prospective_assessments',identifier)
        if not restricted and row['owner']!=identity:raise HTTPException(404,'Record not found')
        return payload if restricted else farmer_assessment(payload)

def record_outcome(repository,value,actor):
    initialize(repository);stamp=now()
    with repository.connection() as db:
        db.execute('BEGIN IMMEDIATE');_,assessment=read_verified(db,'prospective_assessments',value.assessment_id)
        protocol=assessment['protocol']
        if protocol is None:raise HTTPException(422,'Assessment has no preregistered outcome protocol')
        if value.target_definition_version!=protocol['definition_version']:raise HTTPException(422,'Outcome target version mismatch')
        if not (datetime.fromisoformat(assessment['outcome_due_at'])<=value.observed_at<=stamp):raise HTTPException(422,'Outcome must be observed after horizon and no later than server time')
        payload=encoded(dict(value.model_dump(mode='json'),recorded_at=stamp.isoformat(),actor=actor))
        try:db.execute('INSERT INTO prospective_outcomes VALUES(?,?,?,?,?)',(value.assessment_id,payload,digest(payload),stamp.isoformat(),actor))
        except sqlite3.IntegrityError:raise HTTPException(409,'Outcome immutable; adjudicate corrections separately')
    return {'assessment_id':value.assessment_id,'status':'independent_outcome_recorded'}
