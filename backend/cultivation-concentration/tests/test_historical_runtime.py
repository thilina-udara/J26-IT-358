"""No training, real observations or arbitrary artifact deserialization."""
import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services import historical_runtime as runtime
from app.services.historical_prediction import FEATURES, LABEL_DEFINITION, predict_context


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    monkeypatch.setenv('CULTIVATION_HISTORICAL_MODEL','selected_xgboost_2024')
    folder=runtime.BUNDLES['selected_xgboost_2024'][0]
    files={folder+'/selected_xgboost_through_2024.joblib':b'FICTIONAL verified bytes; load mocked, never unpickle',
           folder+'/feature_schema.json':json.dumps({'features':list(FEATURES)}).encode(),
           folder+'/environment.json':json.dumps({'python':platform.python_version(), **{k:version(p) for k,p in
                [('numpy','numpy'),('pandas','pandas'),('sklearn','scikit-learn'),('xgboost','xgboost')]}}).encode()}
    for name,data in files.items():
        path=tmp_path/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    catalog={'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    (tmp_path/'models/artifact_catalog.json').write_text(json.dumps(catalog))
    evidence={'label_definition':LABEL_DEFINITION,'trained_through':2024,'coverage_through':2025,
        'model_sha256':catalog['files'][folder+'/selected_xgboost_through_2024.joblib'],
        'model_available_at':'2025-01-01T00:00:00+00:00','provenance_verified':True,'evidence_reference':'FICTIONAL SOFTWARE FIXTURE',
        'observations':[dict(district='Matara',crop='Corn',season='Maha',year=2025,land_acres=10,production_kg=100,
            observation_end='2025-12-31',available_at='2026-01-01T00:00:00+00:00',provenance_verified=True,evidence_reference='FICTIONAL ONLY')],
        'season_year_mappings':[dict(district='Matara',crop='Corn',season='Maha',planting_start='2030-01-01',planting_end='2030-01-01',
            target_year=2026,available_at='2026-01-01T00:00:00+00:00',verified=True,reference='FICTIONAL not a calendar rule')]}
    def write():
        path=tmp_path/'evidence.json'; data=json.dumps(evidence).encode(); path.write_bytes(data)
        monkeypatch.setenv('CULTIVATION_HISTORICAL_EVIDENCE',str(path))
        monkeypatch.setenv('CULTIVATION_HISTORICAL_EVIDENCE_SHA256',hashlib.sha256(data).hexdigest())
    write()
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from xgboost import XGBClassifier
    preprocessing=ColumnTransformer([]); preprocessing.feature_names_in_=np.array(FEATURES)
    classifier=XGBClassifier(); classifier.n_classes_=3
    model=Pipeline([('preprocessing',preprocessing),('classifier',classifier)])
    monkeypatch.setattr(model,'predict',lambda frame:np.array([1]))
    loaded=[]
    import joblib
    monkeypatch.setattr(joblib,'load',lambda stream:(loaded.append(stream.read()),model)[1])
    return tmp_path,folder,evidence,write,loaded,model


def context(service):
    return predict_context(service,dict(district='Matara',crop='Corn',planting_date='2030-01-01'),
        'Maha',datetime(2026,2,1,tzinfo=timezone.utc))


def test_verified_compatible_loading_and_proxy_separation(bundle):
    service=runtime.provision(); assert bundle[4] and context(service)['status']=='historical_proxy_prediction'
    assert context(service)['risk_level']=='Medium'
    assert service.predict('Matara','Corn','Maha',2024,datetime(2026,2,1,tzinfo=timezone.utc))['risk_level'] is None


@pytest.mark.parametrize('failure',['hash','missing','schema','environment','alias','evidence_hash','missing_evidence','lineage','mapping','model_binding'])
def test_reject_before_deserialization(bundle,monkeypatch,failure):
    root,folder,evidence,write,loaded,_=bundle
    if failure=='hash':(root/folder/'selected_xgboost_through_2024.joblib').write_bytes(b'corrupt')
    if failure=='missing':(root/folder/'selected_xgboost_through_2024.joblib').unlink()
    if failure in ('schema','environment'):
        name=folder+('/feature_schema.json' if failure=='schema' else '/environment.json')
        data=json.dumps({'features':['Land_Size_Acres']} if failure=='schema' else {}).encode()
        (root/name).write_bytes(data); catalog=json.loads((root/'models/artifact_catalog.json').read_text())
        catalog['files'][name]=hashlib.sha256(data).hexdigest(); (root/'models/artifact_catalog.json').write_text(json.dumps(catalog))
    if failure=='alias':monkeypatch.setenv('CULTIVATION_HISTORICAL_MODEL','../../untrusted.joblib')
    if failure=='evidence_hash':monkeypatch.setenv('CULTIVATION_HISTORICAL_EVIDENCE_SHA256','0'*64)
    if failure=='missing_evidence':monkeypatch.delenv('CULTIVATION_HISTORICAL_EVIDENCE')
    if failure=='lineage':evidence['observations'][0]['provenance_verified']=False; write()
    if failure=='mapping':evidence['season_year_mappings'][0]['verified']=False; write()
    if failure=='model_binding':evidence['model_sha256']='0'*64; write()
    assert isinstance(runtime.provision(),runtime.UnavailablePredictor)
    assert loaded==[]


@pytest.mark.parametrize('change',['missing_observations','late_observation','late_model','late_mapping','unsupported_crop','ambiguous_mapping'])
def test_temporal_and_mapping_gates(bundle,change):
    _,_,evidence,write,_,_=bundle
    if change=='missing_observations':evidence['observations']=[]
    if change=='late_observation':evidence['observations'][0]['available_at']='2027-01-01T00:00:00+00:00'
    if change=='late_model':evidence['model_available_at']='2027-01-01T00:00:00+00:00'
    if change=='late_mapping':evidence['season_year_mappings'][0]['available_at']='2027-01-01T00:00:00+00:00'
    if change=='unsupported_crop':evidence['season_year_mappings'][0]['crop']='Brinjal'
    if change=='ambiguous_mapping':evidence['season_year_mappings']*=2
    write(); assert context(runtime.provision())['risk_level'] is None


def test_target_year_observation_never_enters_features(bundle,monkeypatch):
    _,_,evidence,write,_,model=bundle
    evidence['observations'].append(dict(evidence['observations'][0],year=2026,observation_end='2026-12-31',available_at='2027-01-01T00:00:00+00:00',land_acres=999999))
    write(); observed=[]
    monkeypatch.setattr(model,'predict',lambda frame:(observed.append(frame),np.array([1]))[1])
    assert context(runtime.provision())['status']=='historical_proxy_prediction'
    assert observed[0].iloc[0]['Historical_Mean_Land_Acres']==10


def test_existing_workflow_authorization_and_current_risk_gates(bundle):
    root,_,_,_,_,_=bundle
    client=TestClient(create_app(root/'plans.sqlite3',{'owner':'fictional-owner','other':'fictional-other'},[]))
    value=dict(district='Matara',crop='Corn',region='fictional',land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01',season='Maha')
    result=client.post('/api/farmer-workflow/plans',headers={'Authorization':'Bearer owner'},json=value)
    assert result.status_code==201; report=result.json()['workflow']
    assert report['historical_prediction']['status']=='historical_proxy_prediction'
    assert report['assessment']['risk_level'] is None and report['current_plan_risk']['risk_level'] is None
    assert report['recommendations']['alternatives']==[]
    identifier=result.json()['plan']['plan_id']
    assert client.post('/api/farmer-workflow/analyze',json={'plan_id':identifier}).status_code==401
    assert client.post('/api/farmer-workflow/analyze',headers={'Authorization':'Bearer other'},json={'plan_id':identifier}).status_code==404


def test_unavailable_optional_model_does_not_prevent_startup(bundle,monkeypatch):
    monkeypatch.setenv('CULTIVATION_HISTORICAL_MODEL','unknown')
    root=bundle[0]; client=TestClient(create_app(root/'plans.sqlite3',{'owner':'fictional-owner'},[]))
    assert client.get('/health').status_code==200
    result=client.post('/api/farmer-workflow/plans',headers={'Authorization':'Bearer owner'},json=dict(district='Matara',crop='Corn',region='fictional',land_size_acres=2,planting_date='2030-01-01',expected_harvest_date='2030-04-01'))
    assert result.json()['workflow']['historical_prediction']['risk_level'] is None
    assert 'Unsupported historical model alias' in result.text
    assert client.get('/ready').json()['checks']['historical_predictor']['status']=='unavailable'


def test_disabled_and_injected_compatibility(bundle,monkeypatch):
    monkeypatch.delenv('CULTIVATION_HISTORICAL_MODEL')
    assert runtime.provision() is None
    service=runtime.UnavailablePredictor('explicit injected fixture')
    client=TestClient(create_app(bundle[0]/'plans.sqlite3',{},[],historical_predictor=service))
    assert client.get('/health').status_code==200


@pytest.mark.parametrize('failure',['wrong_type','wrong_labels','prediction_error','fractional_label'])
def test_model_compatibility_and_inference_failures(bundle,monkeypatch,failure):
    import joblib
    model=bundle[5]
    if failure=='wrong_type':monkeypatch.setattr(joblib,'load',lambda stream:object())
    if failure=='wrong_labels':model.steps[-1][1].n_classes_=2
    if failure=='prediction_error':
        def broken(frame):raise RuntimeError('fictional private model error')
        monkeypatch.setattr(model,'predict',broken)
    if failure=='fractional_label':monkeypatch.setattr(model,'predict',lambda frame:np.array([1.5]))
    result=context(runtime.provision())
    assert result['risk_level'] is None and 'fictional private model error' not in str(result)
