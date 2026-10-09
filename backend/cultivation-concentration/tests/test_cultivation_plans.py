from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path/'test-plans.sqlite3',{'alice-token':'alice','bob-token':'bob'}))


def payload(**changes):
    value = dict(farmer_id='alice',district='Matara',region=' North ',crop='Corn',
                 land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01')
    value.update(changes)
    return value


def request(client,method,path,value=None,token='alice-token'):
    return client.request(method,path,json=value,headers={'Authorization':'Bearer '+token})


def test_crud_persistence_duplicate_and_cancellation(tmp_path):
    path=tmp_path/'independent.sqlite3'
    client=TestClient(create_app(path,{'alice-token':'alice'}))
    response=request(client,'POST','/api/cultivation-plans',payload())
    assert response.status_code==201
    saved=response.json(); identifier=saved['plan']['plan_id']; endpoint='/api/cultivation-plans/'+identifier
    assert saved['concentration']['plan_count'] is None
    assert saved['plan']['region']=='north'
    assert request(client,'POST','/api/cultivation-plans',payload(land_size_acres=9)).status_code==409
    second=TestClient(create_app(path,{'alice-token':'alice'}))
    assert request(second,'GET',endpoint).json()['plan']['plan_id']==identifier
    updated=request(second,'PUT',endpoint,payload(land_size_acres=3)).json()
    assert updated['concentration']['total_acreage'] is None
    assert updated['plan']['submitted_at']==saved['plan']['submitted_at']
    cancelled=request(second,'DELETE',endpoint).json()
    assert cancelled['plan']['status']=='cancelled'
    assert cancelled['concentration']['plan_count'] is None
    assert request(second,'DELETE',endpoint).json()['plan']['updated_at']==cancelled['plan']['updated_at']
    assert request(second,'GET',endpoint).status_code==200


def test_overlap_boundaries_filters_and_privacy(client):
    base=request(client,'POST','/api/cultivation-plans',payload()).json()
    for days in (-15,-14,14,15):
        harvest=(date(2030,4,1)+timedelta(days=days)).isoformat()
        assert request(client,'POST','/api/cultivation-plans',payload(farmer_id='bob',expected_harvest_date=harvest),token='bob-token').status_code==201
    for changes in ({'region':'south'},{'district':'Hambantota'},{'crop':'Brinjal'},{'status':'cancelled'}):
        assert request(client,'POST','/api/cultivation-plans',payload(farmer_id='bob',**changes),token='bob-token').status_code==201
    endpoint='/api/cultivation-plans/'+base['plan']['plan_id']
    result=request(client,'GET',endpoint).json()
    assert result['concentration']['plan_count'] is None
    assert result['concentration']['total_acreage'] is None
    assert result['concentration']['harvest_window_start']=='2030-03-18'
    assert result['concentration']['harvest_window_end']=='2030-04-15'
    assert 'bob' not in str(result)
    for method in ('GET','PUT','DELETE'):
        assert request(client,method,endpoint,payload(farmer_id='bob') if method=='PUT' else None,token='bob-token').status_code==404


@pytest.mark.parametrize('changes',[{'district':'Colombo'},{'crop':'Tomato'},{'land_size_acres':0},
    {'land_size_acres':-1},{'planting_date':'bad'},{'expected_harvest_date':'2029-01-01'},
    {'region':'   '},{'status':'deleted'},{'plan_id':'client-supplied'}])
def test_invalid_inputs(client,changes):
    assert request(client,'POST','/api/cultivation-plans',payload(**changes)).status_code==422


def test_authentication_and_identity(client):
    assert client.post('/api/cultivation-plans',json=payload()).status_code==401
    assert request(client,'POST','/api/cultivation-plans',payload(farmer_id='bob')).status_code==403
    assert request(client,'GET','/api/cultivation-plans/missing',token='invalid').status_code==401


def test_conflicting_update_rolls_back(client):
    first=request(client,'POST','/api/cultivation-plans',payload()).json()['plan']['plan_id']
    second=request(client,'POST','/api/cultivation-plans',payload(region='south')).json()['plan']['plan_id']
    assert request(client,'PUT','/api/cultivation-plans/'+second,payload()).status_code==409
    assert request(client,'GET','/api/cultivation-plans/'+second).json()['plan']['region']=='south'
    assert request(client,'GET','/api/cultivation-plans/'+first).json()['concentration']['plan_count'] is None
