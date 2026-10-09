from datetime import datetime, timezone
import json
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.privacy import NUMERIC_AGGREGATES, analyst_view


def contains_collective_numbers(value):
    if isinstance(value,list):return any(contains_collective_numbers(v) for v in value)
    if isinstance(value,dict):
        return any((k in NUMERIC_AGGREGATES and isinstance(v,(int,float))) or contains_collective_numbers(v) for k,v in value.items())
    return False


def test_roles_owner_snapshot_and_differencing(tmp_path):
    client=TestClient(create_app(tmp_path/'roles.sqlite3',{'alice':'alice','bob':'bob'},['analyst'],admin_tokens=['admin']))
    body=dict(farmer_id='alice',district='Matara',region='north',crop='Corn',land_size_acres=2,
        planting_date='2030-01-01',expected_harvest_date='2030-04-01')
    def headers(token):return {'Authorization':'Bearer '+token}
    alice=client.post('/api/cultivation-plans',headers=headers('alice'),json=body).json()
    identifier=alice['plan']['plan_id'];cutoff=datetime.now(timezone.utc).isoformat()
    client.post('/api/cultivation-plans',headers=headers('bob'),json=dict(body,farmer_id='bob',land_size_acres=17))
    endpoint='/api/cultivation-plans/'+identifier+'/risk-assessment'
    for token in ('bob','analyst','admin','invalid'):
        assert client.get(endpoint,headers=headers(token),params={'season':'Maha'}).status_code in (401,404)
    for changes in ({},{'land_size_acres':10},{'region':'south'},{'expected_harvest_date':'2030-04-02'}):
        response=client.put('/api/cultivation-plans/'+identifier,headers=headers('alice'),json=dict(body,**changes))
        assert response.status_code==200
        assert not contains_collective_numbers(response.json()['concentration'])
        assessment=client.get(endpoint,headers=headers('alice'),params={'season':'Maha'})
        assert assessment.status_code==200 and not contains_collective_numbers(assessment.json())
        assert 'bob' not in json.dumps(assessment.json())
    historical=client.get(endpoint,headers=headers('alice'),params={'season':'Maha','as_of':cutoff})
    assert historical.status_code==200 and historical.json()['indicators']['region']=='north'
    for token in ('analyst','admin'):
        assert client.get('/api/cultivation-analysis/clusters',headers=headers(token),params={'district':'Matara'}).status_code==200
        assert client.get('/api/cultivation-plans/'+identifier,headers=headers(token)).status_code==401
    for url in ('clusters','risk-indicators','risk-assessment'):
        params=dict(district='Matara',region='north',crop='Corn',season='Maha',harvest_date='2030-04-01')
        assert client.get('/api/cultivation-analysis/'+url,headers=headers('alice'),params=params).status_code==403
    assert client.get(endpoint,params={'season':'Maha'}).status_code==401


def test_complementary_suppression():
    released=analyst_view(dict(kmeans=[dict(status='available',planned_acreage=10),dict(status='suppressed')],
        dbscan=[dict(status='available',planned_acreage=10)],noise=dict(status='suppressed'),baseline=[]))
    assert not contains_collective_numbers(released)


def test_fail_closed_role_configuration(tmp_path,monkeypatch):
    client=TestClient(create_app(tmp_path/'ambiguous.sqlite3',{'same':'alice'},['same']))
    assert client.get('/api/cultivation-plans/missing',headers={'Authorization':'Bearer same'}).status_code==503
    monkeypatch.setenv('CULTIVATION_FARMER_TOKENS','broken-json')
    client=TestClient(create_app(tmp_path/'invalid.sqlite3'))
    response=client.get('/api/cultivation-plans/missing',headers={'Authorization':'Bearer secret'})
    assert response.status_code==503 and 'secret' not in response.text
