"""Fictional declarations: never substitute them for approved statistical mappings."""
import json
import sqlite3
from datetime import datetime, timezone

import pytest
from app.migrations import migrate, MIGRATIONS
from app.schemas.cultivation_plan import Plan, PlanInput
from app.services.cultivation_plans import PlanStore
from app.services.plan_clustering import snapshot
from tests.test_farmer_auth import account, headers, plan
from tests.test_farmer_workflow_e2e import client_for


def test_existing_database_migration_is_additive_and_repeatable(tmp_path):
    path = tmp_path/'legacy.sqlite3'
    # The pre-migration schema, including a genuine legacy version payload.
    from pathlib import Path
    script = (Path(__file__).parents[1]/'app/migrations/002_farmer_declared_season.sql').read_text()
    legacy = dict(plan(), farmer_id='fictional-owner', plan_id='legacy', status='active',
                  submitted_at='2021-01-01T00:00:00+00:00', updated_at='2022-01-01T00:00:00+00:00')
    with sqlite3.connect(path) as db:
        db.execute(script.split(';')[0])
        db.execute('CREATE TABLE cultivation_plan_versions (version_id INTEGER PRIMARY KEY, plan_id TEXT, recorded_at TEXT, payload TEXT)')
        db.execute('INSERT INTO cultivation_plans ('+','.join(legacy)+') VALUES ('+','.join('?' for _ in legacy)+')', list(legacy.values()))
        payload=json.dumps(legacy)
        db.execute('INSERT INTO cultivation_plan_versions VALUES (1,?,?,?)', ('legacy',legacy['updated_at'],payload))
    migrate(path)
    migrate(path)
    store=PlanStore(path)
    saved=store.read('legacy','fictional-owner')['plan']
    assert saved.farmer_declared_season is None
    assert saved.submitted_at.isoformat()==legacy['submitted_at']
    assert saved.updated_at.isoformat()==legacy['updated_at']
    with store.connection() as db:
        assert db.execute('SELECT payload FROM cultivation_plan_versions').fetchone()[0]==payload
        assert dict(db.execute('SELECT version,name FROM component02_schema_migrations'))==dict(MIGRATIONS)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE cultivation_plans SET farmer_declared_season='Invented'")
    assert Plan.model_validate_json(payload).farmer_declared_season is None


def test_revision_cutoffs_preservation_clear_cancel_and_restart(tmp_path):
    path=tmp_path/'versions.sqlite3'; store=PlanStore(path)
    value=PlanInput(**plan(), farmer_id='fictional-owner', farmer_declared_season='Maha')
    created=store.save(value,'fictional-owner')['plan']; identifier=created.plan_id
    first_cutoff=created.updated_at
    changed=store.save(value.model_copy(update={'farmer_declared_season':'Yala'}),'fictional-owner',identifier)['plan']
    assert changed.submitted_at==created.submitted_at and changed.updated_at>created.updated_at
    assert snapshot(store,first_cutoff)[0]['farmer_declared_season']=='Maha'
    assert PlanStore(path).read(identifier,'fictional-owner')['plan'].farmer_declared_season=='Yala'
    omitted=PlanInput(**plan(),farmer_id='fictional-owner')
    assert store.save(omitted,'fictional-owner',identifier)['plan'].farmer_declared_season=='Yala'
    assert store.cancel(identifier,'fictional-owner')['plan'].farmer_declared_season=='Yala'
    assert store.save(omitted.model_copy(update={'farmer_declared_season':None}), 'fictional-owner',identifier)['plan'].farmer_declared_season is None
    with store.connection() as db:
        versions=[Plan.model_validate_json(r[0]) for r in db.execute('SELECT payload FROM cultivation_plan_versions ORDER BY version_id')]
    assert [v.farmer_declared_season for v in versions]==['Maha','Yala','Yala','Yala',None]


def test_workflow_context_conflict_is_read_only_and_scoped(tmp_path):
    path=tmp_path/'workflow.sqlite3'; client=client_for(path)
    _,session=account(client); h=headers(session['access_token'])
    _,other=account(client,'fictional-peer'); peer=headers(other['access_token'])
    result=client.post('/api/farmer-workflow/plans',headers=h,json=dict(plan(),season='Maha'))
    assert result.status_code==201,result.text
    saved=result.json()['plan']; identifier=saved['plan_id']
    assert saved['farmer_declared_season']=='Maha'
    endpoint='/api/farmer-workflow/analyze'
    implicit=client.post(endpoint,headers=h,json=dict(plan_id=identifier)).json()
    assert implicit['season_context']['effective_analysis_season']=='Maha'
    assert implicit['season_context']['source']=='farmer_declaration'
    conflicting=client.post(endpoint,headers=h,json=dict(plan_id=identifier,season='Yala')).json()
    assert conflicting['season_context']['conflict'] is True
    assert conflicting['season_context']['effective_analysis_season']=='Yala'
    assert conflicting['season_context']['farmer_declared_season']=='Maha'
    assert conflicting['season_context']['independently_verified_statistical_season'] is None
    assert conflicting['assessment']['risk_level'] is None
    assert conflicting['historical_prediction']['status']=='insufficient_evidence'
    assert conflicting['recommendations']['alternatives']==[]
    assert client.post(endpoint,headers=peer,json=dict(plan_id=identifier)).status_code==404
    assert client.get('/api/cultivation-plans/'+identifier,headers=peer).status_code==404
    assert client.get('/api/cultivation-plans',headers=peer).json()['items']==[]
    assert client_for(path).get('/api/cultivation-plans/'+identifier,headers=h).json()['plan']==saved


@pytest.mark.parametrize('invalid',['maha','Unknown',1,{'verified':True}])
def test_invalid_declaration_rejected(tmp_path,invalid):
    client=client_for(tmp_path/'invalid.sqlite3'); _,s=account(client); h=headers(s['access_token'])
    assert client.post('/api/cultivation-plans',headers=h,json=dict(plan(),farmer_declared_season=invalid)).status_code==422
    assert client.post('/api/farmer-workflow/plans',headers=h,json=dict(plan(),season=invalid)).status_code==422


def test_historical_declaration_keeps_actual_server_timestamps(tmp_path):
    client=client_for(tmp_path/'past.sqlite3'); _,s=account(client); h=headers(s['access_token'])
    before=datetime.now(timezone.utc)
    saved=client.post('/api/cultivation-plans',headers=h,json=plan(planting_date='2020-01-01',expected_harvest_date='2020-04-01',farmer_declared_season='Yala')).json()['plan']
    assert datetime.fromisoformat(saved['submitted_at'])>=before
    report=client.post('/api/farmer-workflow/analyze',headers=h,json=dict(plan_id=saved['plan_id'])).json()
    assert report['analysis_status']=='not_applicable'
    assert report['season_context']['farmer_declared_season']=='Yala'


def test_personalized_save_preserves_declaration_and_season_update_is_stale(tmp_path):
    client=client_for(tmp_path/'planning.sqlite3'); _,s=account(client); h=headers(s['access_token'])
    saved=client.post('/api/cultivation-plans',headers=h,json=plan(farmer_declared_season='Maha')).json()['plan']
    identifier=saved['plan_id']; base='/api/cultivation-plans/'+identifier
    request=dict(plan_id=identifier,final_crop='Corn',**{k:v for k,v in plan().items() if k!='crop'},season='Yala')
    result=client.post('/api/personalized-cultivation-plans/save',headers=h,json=request)
    assert result.status_code==200,result.text
    assert result.json()['stale'] is False
    assert client.get(base,headers=h).json()['plan']['farmer_declared_season']=='Maha'
    assert client.put(base,headers=h,json=plan(farmer_declared_season='Yala')).status_code==200
    assert client.get('/api/personalized-cultivation-plans/'+identifier,headers=h).json()['stale'] is True


def test_legacy_workflow_omitted_season_stays_unknown(tmp_path):
    client=client_for(tmp_path/'unknown.sqlite3'); _,s=account(client); h=headers(s['access_token'])
    result=client.post('/api/farmer-workflow/plans',headers=h,json=plan())
    assert result.status_code==201
    assert result.json()['plan']['farmer_declared_season'] is None
    assert result.json()['workflow']['season_context']['source']=='unknown'
