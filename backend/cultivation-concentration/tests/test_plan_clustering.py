from datetime import datetime, timezone
import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas.cultivation_plan import Plan
from app.services.cultivation_plans import PlanStore
from app.services.plan_clustering import snapshot, analyze


def plan(i,**changes):
    value=dict(plan_id=f'plan-{i}',farmer_id=f'farmer-{i}',district='Matara',region='north',crop='Corn',
        land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01',status='active',
        submitted_at='2020-01-01T00:00:00+00:00',updated_at='2020-01-01T00:00:00+00:00')
    value.update(changes)
    return Plan.model_validate(value)


def test_snapshot_no_future_submission_or_revision_and_cancellation(tmp_path):
    store=PlanStore(tmp_path/'fictional.sqlite3')
    with store.connection() as db:
        store.record_version(db,plan(1))
        store.record_version(db,plan(1,land_size_acres=90,updated_at='2021-01-01T00:00:00+00:00'))
        store.record_version(db,plan(2,submitted_at='2021-01-01T00:00:00+00:00',updated_at='2021-01-01T00:00:00+00:00'))
        store.record_version(db,plan(3,status='cancelled'))
        store.record_version(db,plan(4,planting_date='2019-01-01'))
    old=snapshot(store,datetime(2020,6,1,tzinfo=timezone.utc))
    assert len(old)==1 and old[0]['land_size_acres']==2
    recent=snapshot(store,datetime(2021,6,1,tzinfo=timezone.utc))
    assert len(recent)==2 and recent[0]['land_size_acres']==90
    with store.connection() as db:
        store.record_version(db,plan(1,status='cancelled',updated_at='2022-01-01T00:00:00+00:00'))
    assert len(snapshot(store,datetime(2022,6,1,tzinfo=timezone.utc)))==1


def test_clusters_identical_plans_and_noise_not_risk():
    records=[plan(i).model_dump(mode='json') for i in range(6)]
    result=analyze(records,'Matara')
    assert result['effective_k']==1
    for group in (result['kmeans'][0],result['dbscan'][0],result['baseline'][0]):
        assert group['plan_count']==6 and group['farmer_count']==6
        assert group['planned_acreage']==12
        assert group['peak_plan_centered_29_day_planned_acreage']==12
    assert result==analyze(list(reversed(records)),'Matara')
    text=json.dumps(result)
    assert 'farmer-0' not in text and 'plan-0' not in text
    assert 'high-risk' in result['noise']['meaning']  # explicitly denies this interpretation
    assert 'risk_label' not in text


def test_separated_groups_and_private_outlier():
    records=[plan(i).model_dump(mode='json') for i in range(3)]
    records += [plan(i,crop='Brinjal',region='south',expected_harvest_date='2030-10-01').model_dump(mode='json') for i in range(3,6)]
    records += [plan(6,land_size_acres=200,expected_harvest_date='2031-10-01').model_dump(mode='json')]
    result=analyze(records,'Matara',clusters=2,eps=.1,min_samples=3)
    assert len(result['dbscan'])==2
    assert result['noise']['status']=='suppressed'
    assert 'planned_acreage' not in result['noise']
    assert all(g['farmer_count']==3 for g in result['dbscan'])


def test_insufficient_empty_and_one_farmer():
    assert analyze([],'Matara')['status']=='insufficient_or_private'
    records=[plan(i,farmer_id='same').model_dump(mode='json') for i in range(10)]
    assert analyze(records,'Matara')['status']=='insufficient_or_private'


def test_endpoint_auth_cutoff_and_future_only(tmp_path):
    dbpath=tmp_path/'api.sqlite3'
    store=PlanStore(dbpath)
    with store.connection() as db:
        for i in range(6):
            store.record_version(db,plan(i))
    client=TestClient(create_app(dbpath,{'farmer-token':'farmer-0'},['analyst-token']))
    endpoint='/api/cultivation-analysis/clusters'
    assert client.get(endpoint,params={'district':'Matara'}).status_code==403
    assert client.get(endpoint,params={'district':'Matara'},headers={'Authorization':'Bearer farmer-token'}).status_code==403
    headers={'Authorization':'Bearer analyst-token'}
    result=client.get(endpoint,params={'district':'Matara','as_of':'2020-06-01T00:00:00Z'},headers=headers)
    assert result.status_code==200 and result.json()['kmeans'][0]['planned_acreage']==12
    for parameters in ({'as_of':'2020-06-01T00:00:00'},{'as_of':'2099-01-01T00:00:00Z'},{'k':0},{'eps':0},{'district':'Colombo'}):
        assert client.get(endpoint,params={'district':'Matara',**parameters},headers=headers).status_code==422


def test_existing_row_migration_not_backdated(tmp_path):
    store=PlanStore(tmp_path/'migration.sqlite3')
    existing=plan(1,updated_at='2021-01-01T00:00:00+00:00').model_dump(mode='json')
    with store.connection() as db:
        db.execute('INSERT INTO cultivation_plans ('+','.join(existing)+') VALUES ('+','.join('?' for _ in existing)+')',list(existing.values()))
    migrated=PlanStore(store.path)
    assert snapshot(migrated,datetime(2020,6,1,tzinfo=timezone.utc))==[]
    assert len(snapshot(migrated,datetime(2021,6,1,tzinfo=timezone.utc)))==1


def test_crud_records_revision_history(tmp_path):
    path=tmp_path/'revision.sqlite3'
    client=TestClient(create_app(path,{'secret':'farmer-0'}))
    headers={'Authorization':'Bearer secret'}
    body=plan(0).model_dump(mode='json')
    for field in ('plan_id','submitted_at','updated_at'):
        body.pop(field)
    saved=client.post('/api/cultivation-plans',json=body,headers=headers).json()['plan']
    cutoff=datetime.fromisoformat(saved['updated_at'])
    body['land_size_acres']=5
    assert client.put('/api/cultivation-plans/'+saved['plan_id'],json=body,headers=headers).status_code==200
    store=PlanStore(path)
    assert snapshot(store,cutoff)[0]['land_size_acres']==2
    assert client.delete('/api/cultivation-plans/'+saved['plan_id'],headers=headers).status_code==200
    assert snapshot(store,datetime.now(timezone.utc))==[]
