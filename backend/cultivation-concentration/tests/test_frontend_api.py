"""Frontend contracts use fictional identities and temporary SQLite only."""
import json
import sqlite3
from contextlib import closing, contextmanager
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.cultivation_plans import PlanStore
from app.services.farmer_auth import AuthStore
from app.services import farmer_auth, readiness
from tests.test_farmer_auth import account, headers, plan

PATH = '/api/cultivation-plans'
OWNER = headers('fictional-owner-token')
OTHER = headers('fictional-other-token')
ORIGIN = 'http://localhost:5173'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('CULTIVATION_CORS_ORIGINS', '[]')
    monkeypatch.setenv('CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED', 'true')
    monkeypatch.setenv('CULTIVATION_SESSION_TTL_SECONDS', '3600')
    return TestClient(create_app(tmp_path / 'frontend.sqlite3',
        {'fictional-owner-token': 'fictional-owner', 'fictional-other-token': 'fictional-other'},
        ['fictional-analyst'], admin_tokens=['fictional-admin'], reviewer_tokens={'fictional-reviewer': 'expert'}))


@pytest.fixture
def seeded(client):
    specs = [('Corn','Matara',False), ('Corn','Matara',True), ('Brinjal','Matara',False),
             ('Corn','Hambantota',False), ('Bandakka','Hambantota',True), ('Brinjal','Hambantota',False)]
    expected = []
    for i, (crop, district, cancelled) in enumerate(specs):
        response = client.post(PATH, headers=OWNER, json=plan(region=f'fictional-region-{i}', crop=crop, district=district))
        assert response.status_code == 201
        record = response.json()['plan']
        if cancelled:
            record = client.delete(PATH + '/' + record['plan_id'], headers=OWNER).json()['plan']
        expected.append(record)
    assert client.post(PATH, headers=OTHER, json=plan(region='fictional-private-other')).status_code == 201
    return client, sorted(expected, key=lambda p: (p['submitted_at'],p['plan_id']), reverse=True)


def test_empty_authenticated_listing(client):
    response = client.get(PATH, headers=OWNER)
    assert response.status_code == 200
    assert response.json() == dict(items=[],total=0,limit=20,offset=0,has_more=False,next_offset=None)
    assert response.headers['cache-control'] == 'no-store'


def test_listing_returns_current_owned_records_only(seeded):
    client, expected = seeded
    result = client.get(PATH, headers=OWNER).json()
    assert result['items'] == expected and result['total'] == 6
    assert all(p['farmer_id'] == 'fictional-owner' for p in result['items'])
    assert sum(p['status'] == 'cancelled' for p in result['items']) == 2
    assert 'fictional-private-other' not in json.dumps(result)
    other = client.get(PATH, headers=OTHER).json()
    assert other['total'] == 1 and other['items'][0]['farmer_id'] == 'fictional-other'


def test_pagination_boundaries_and_stable_order(seeded):
    client, expected = seeded
    pages = []
    for offset in (0,2,4):
        response = client.get(PATH, headers=OWNER, params=dict(limit=2,offset=offset))
        result = response.json()
        assert result['items'] == expected[offset:offset+2]
        assert result['total'] == 6
        assert result['has_more'] == (offset < 4)
        assert result['next_offset'] == (offset+2 if offset < 4 else None)
        pages.extend(result['items'])
    assert pages == expected
    assert client.get(PATH, headers=OWNER, params={'limit': 1}).json()['items'] == expected[:1]
    assert client.get(PATH, headers=OWNER, params={'limit': 100}).json()['items'] == expected
    for offset in (6,7,1_000_000):
        result = client.get(PATH, headers=OWNER, params={'offset': offset}).json()
        assert result['items'] == [] and result['total'] == 6
        assert not result['has_more'] and result['next_offset'] is None


@pytest.mark.parametrize('params', [
    {'limit':0}, {'limit':101}, {'limit':-1}, {'limit':'1.5'}, {'offset':-1}, {'offset':1_000_001},
    {'status':'deleted'}, {'crop':'Tomato'}, {'district':'Colombo'}, {'crop':"Corn' OR 1=1 --"},
    {'farmer_id':'fictional-other'}, {'sort':'farmer_id'},
])
def test_invalid_listing_queries_are_rejected(client, params):
    assert client.get(PATH, headers=OWNER, params=params).status_code == 422


def test_repeated_query_parameters_are_rejected(client):
    assert client.get(PATH, headers=OWNER, params=[('status','active'),('status','cancelled')]).status_code == 422


@pytest.mark.parametrize('params', [
    {'status':'active'}, {'status':'cancelled'}, {'crop':'Corn'}, {'district':'Hambantota'},
    {'status':'active','crop':'Corn','district':'Matara'},
    {'status':'cancelled','crop':'Brinjal','district':'Matara'},
])
def test_filtering_and_filtered_total(seeded, params):
    client, records = seeded
    expected = [p for p in records if all(p[key] == value for key,value in params.items())]
    result = client.get(PATH, headers=OWNER, params=dict(params,limit=1)).json()
    assert result['total'] == len(expected) and result['items'] == expected[:1]
    assert result['has_more'] == (len(expected) > 1)


@pytest.mark.parametrize('token', [None,'invalid','cc_session_' + 'x'*43,
    'fictional-analyst','fictional-admin','fictional-reviewer'])
def test_listing_rejects_unauthorized_and_research_roles(client, token):
    response = client.get(PATH, headers=headers(token) if token else {})
    assert response.status_code == 401


def test_session_listing_expiry_and_cross_farmer_isolation(client, monkeypatch):
    clock = [2_000_000_000]
    monkeypatch.setattr(farmer_auth,'now_seconds',lambda:clock[0])
    farmer, session = account(client, 'fictional-account-owner')
    other, other_session = account(client, 'fictional-account-other')
    first = client.post(PATH, headers=headers(session['access_token']), json=plan())
    assert first.status_code == 201
    record = first.json()['plan']
    result = client.get(PATH, headers=headers(session['access_token'])).json()
    assert result['items'] == [record] and record['farmer_id'] == farmer['farmer_id']
    assert client.get(PATH, headers=headers(other_session['access_token'])).json()['items'] == []
    assert client.get(PATH + '/' + record['plan_id'], headers=headers(other_session['access_token'])).status_code == 404
    assert client.get(PATH, headers=headers(session['access_token']), params={'farmer_id':other['farmer_id']}).status_code == 422
    clock[0] += session['expires_in']
    assert client.get(PATH, headers=headers(session['access_token'])).status_code == 401


def test_listing_persists_and_does_not_mutate_revisions(seeded, tmp_path):
    client, expected = seeded
    path = tmp_path / 'frontend.sqlite3'
    with closing(sqlite3.connect(path)) as db:
        before = db.execute('SELECT * FROM cultivation_plan_versions ORDER BY version_id').fetchall()
    restarted = TestClient(create_app(path, {'fictional-owner-token':'fictional-owner'}))
    assert restarted.get(PATH, headers=OWNER).json()['items'] == expected
    updated = restarted.put(PATH + '/' + expected[0]['plan_id'], headers=OWNER,
        json=plan(crop=expected[0]['crop'], district=expected[0]['district'], region=expected[0]['region'], land_size_acres=9,
                  status=expected[0]['status']))
    assert updated.status_code == 200
    assert restarted.get(PATH, headers=OWNER).json()['items'][0]['land_size_acres'] == 9
    with closing(sqlite3.connect(path)) as db:
        after = db.execute('SELECT * FROM cultivation_plan_versions ORDER BY version_id').fetchall()
    assert after[:len(before)] == before and len(after) == len(before)+1


def test_listing_uses_indexed_database_pagination(seeded, tmp_path):
    _, expected = seeded
    repository = PlanStore(tmp_path / 'frontend.sqlite3')
    queries = []
    connection = repository.connection
    @contextmanager
    def traced():
        with connection() as db:
            db.set_trace_callback(queries.append)
            yield db
    repository.connection = traced
    result = repository.list_owned('fictional-owner',2,1)
    assert [p.plan_id for p in result['items']] == [p['plan_id'] for p in expected[1:3]]
    selects = [q for q in queries if q.startswith('SELECT')]
    assert len(selects) == 2 and 'COUNT(*)' in selects[0]
    assert 'LIMIT 2 OFFSET 1' in selects[1]
    assert all("farmer_id='fictional-owner'" in q for q in selects)
    with repository.connection() as db:
        for condition,index in (('', 'plan_owner_listing'), (' AND status=?','plan_owner_status_listing'),
                                (' AND crop=?','plan_owner_crop_listing'), (' AND district=?','plan_owner_district_listing')):
            value = 'active' if 'status' in condition else 'Corn' if 'crop' in condition else 'Matara'
            params = ['fictional-owner'] + ([value] if condition else [])
            query = db.execute('EXPLAIN QUERY PLAN SELECT * FROM cultivation_plans WHERE farmer_id=?' + condition +
                ' ORDER BY submitted_at DESC,plan_id DESC LIMIT 2 OFFSET 1', params).fetchall()
            assert any(index in row['detail'] for row in query)


def cors_client(tmp_path, monkeypatch, origins=None):
    monkeypatch.setenv('CULTIVATION_CORS_ORIGINS', json.dumps(origins if origins is not None else [ORIGIN]))
    return TestClient(create_app(tmp_path/'cors.sqlite3', {'fictional-owner-token':'fictional-owner'}))


def preflight(client, origin=ORIGIN, method='GET', request_headers='authorization,content-type'):
    return client.options(PATH, headers={'Origin':origin,'Access-Control-Request-Method':method,
                                        'Access-Control-Request-Headers':request_headers})


def test_cors_allowed_origins_preflight_and_authenticated_response(tmp_path, monkeypatch):
    client = cors_client(tmp_path,monkeypatch,[ORIGIN,'http://127.0.0.1:3000'])
    for origin in (ORIGIN,'http://127.0.0.1:3000'):
        for method in ('GET','POST','PUT','DELETE'):
            response = preflight(client,origin,method)
            assert response.status_code == 200
            assert response.headers['access-control-allow-origin'] == origin
            assert 'authorization' in response.headers['access-control-allow-headers'].lower()
            assert '*' not in response.headers['access-control-allow-origin']
            assert 'access-control-allow-credentials' not in response.headers
    response = client.get(PATH,headers=dict(OWNER,Origin=ORIGIN))
    assert response.status_code == 200 and response.headers['access-control-allow-origin'] == ORIGIN


def test_cors_rejects_other_origins_methods_and_headers(tmp_path, monkeypatch):
    client = cors_client(tmp_path,monkeypatch)
    for origin in ('https://untrusted.example','http://localhost:5174','null'):
        response = preflight(client,origin)
        assert response.status_code == 400 and 'access-control-allow-origin' not in response.headers
        # CORS is a browser policy, not a replacement for bearer authorization.
        response = client.get(PATH,headers=dict(OWNER,Origin=origin))
        assert 'access-control-allow-origin' not in response.headers
    assert preflight(client,method='PATCH').status_code == 400
    assert preflight(client,request_headers='authorization,x-untrusted-header').status_code == 400


def test_cors_error_responses_keep_auth_contract(tmp_path, monkeypatch):
    client = cors_client(tmp_path,monkeypatch)
    response = client.get(PATH,headers={'Origin':ORIGIN})
    assert response.status_code == 401
    assert response.headers['access-control-allow-origin'] == ORIGIN
    assert 'WWW-Authenticate' in response.headers['access-control-expose-headers']
    assert response.headers['www-authenticate'] == 'Bearer'
    login = client.post('/auth/login', headers={'Origin':ORIGIN},json={'login_identifier':'fictional-invalid','password':'wrong'})
    assert login.status_code == 401 and login.headers['cache-control'] == 'no-store'
    assert login.headers['access-control-allow-origin'] == ORIGIN


def test_cors_default_has_no_allowed_origins(tmp_path, monkeypatch):
    monkeypatch.delenv('CULTIVATION_CORS_ORIGINS',raising=False)
    client = TestClient(create_app(tmp_path/'empty-origins.sqlite3', {}))
    assert preflight(client).status_code == 400
    assert 'access-control-allow-origin' not in client.get('/health',headers={'Origin':ORIGIN}).headers


@pytest.mark.parametrize('value', [
    'broken-json','"*"','["*"]','["https://*.example"]','{}','null','[null]',
    '["null"]','["file://localhost"]','["http://"]','["https://example/path"]',
    '["https://example/"]','["https://user:secret@example"]','["https://example?query"]',
    '["https://example#fragment"]','["http://localhost:99999"]','["https://bad host"]',
])
def test_invalid_cors_configuration_fails_closed(tmp_path, monkeypatch, value):
    monkeypatch.setenv('CULTIVATION_CORS_ORIGINS',value)
    with pytest.raises(ValueError,match='CULTIVATION_CORS_ORIGINS'):
        create_app(tmp_path/'invalid-cors.sqlite3', {})


def initialize(path):
    AuthStore(path)
    PlanStore(path)


def test_health_remains_lazy_and_readiness_does_not_create_database(client, tmp_path):
    path = tmp_path/'frontend.sqlite3'
    assert client.get('/health').json() == {'status':'healthy'}
    response = client.get('/ready')
    assert response.status_code == 503 and response.json()['status'] == 'not_ready'
    assert response.json()['checks']['database']['status'] == 'not_initialized'
    assert not path.exists()
    assert client.get('/health').status_code == 200


def test_initialized_readiness_is_independent_of_research_validation(client, tmp_path):
    path = tmp_path/'frontend.sqlite3'
    initialize(path)
    before = path.read_bytes()
    response = client.get('/ready')
    assert response.status_code == 200 and response.json()['status'] == 'ready'
    assert response.json()['research_validation'] == 'not_asserted'
    assert response.json()['checks']['historical_predictor']['status'] == 'not_configured'
    assert response.headers['cache-control'] == 'no-store'
    assert path.read_bytes() == before


def test_missing_or_present_optional_artifacts_are_never_validated(client, tmp_path, monkeypatch):
    initialize(tmp_path/'frontend.sqlite3')
    root = tmp_path/'fictional-model-root'
    folder = root/'models'
    folder.mkdir(parents=True)
    catalog = folder/'artifact_catalog.json'
    monkeypatch.setattr(readiness,'MODEL_CATALOG',catalog)
    assert client.get('/ready').json()['checks']['model_artifacts']['status'] == 'missing'
    catalog.write_text(json.dumps({'files':{'models/fixture.joblib':'fictional-unused-hash'}}))
    response = client.get('/ready')
    assert response.status_code == 200 and response.json()['checks']['model_artifacts']['status'] == 'missing'
    (folder/'fixture.joblib').write_bytes(b'Fictional presence fixture, never loaded')
    result = client.get('/ready').json()
    assert result['checks']['model_artifacts']['status'] == 'present_not_validated'
    assert result['checks']['model_artifacts']['required'] is False
    assert result['research_validation'] == 'not_asserted'


def test_invalid_optional_metadata_is_reported_without_blocking_core(client, tmp_path, monkeypatch):
    initialize(tmp_path/'frontend.sqlite3')
    catalog = tmp_path/'bad-catalog.json'
    catalog.write_text('invalid-json')
    monkeypatch.setattr(readiness,'MODEL_CATALOG',catalog)
    response = client.get('/ready')
    assert response.status_code == 200 and response.json()['checks']['model_artifacts']['status'] == 'unavailable'


def test_missing_auth_schema_or_migration_blocks_readiness(client, tmp_path):
    path = tmp_path/'frontend.sqlite3'
    PlanStore(path)
    assert client.get('/ready').status_code == 503
    AuthStore(path)
    with closing(sqlite3.connect(path)) as db:
        db.execute('DELETE FROM component02_schema_migrations')
        db.commit()
    result = client.get('/ready')
    assert result.status_code == 503 and result.json()['checks']['database']['status'] == 'not_initialized'


def test_unavailable_database_is_redacted(client, tmp_path):
    (tmp_path/'frontend.sqlite3').write_bytes(b'Fictional invalid database')
    response = client.get('/ready')
    assert response.status_code == 503
    assert str(tmp_path) not in response.text
    assert response.json()['checks']['database']['status'] == 'unavailable'


def test_read_only_database_fails_write_probe(client, tmp_path, monkeypatch):
    initialize(tmp_path/'frontend.sqlite3')
    connect = sqlite3.connect
    def read_only(*args,**kwargs):
        db = connect(*args,**kwargs)
        db.execute('PRAGMA query_only=ON')
        return db
    monkeypatch.setattr(readiness.sqlite3,'connect',read_only)
    assert client.get('/ready').status_code == 503


def test_busy_database_blocks_readiness(client, tmp_path):
    initialize(tmp_path/'frontend.sqlite3')
    with closing(sqlite3.connect(tmp_path/'frontend.sqlite3')) as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            assert client.get('/ready').status_code == 503
        finally:
            db.rollback()


@pytest.mark.parametrize('name,value', [
    ('CULTIVATION_SESSION_TTL_SECONDS','invalid'),
    ('CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED','invalid'),
])
def test_invalid_authentication_config_blocks_readiness(client, tmp_path, monkeypatch, name, value):
    initialize(tmp_path/'frontend.sqlite3')
    monkeypatch.setenv(name,value)
    response = client.get('/ready')
    assert response.status_code == 503 and response.json()['checks']['authentication']['status'] == 'unavailable'


def test_ambiguous_research_roles_block_readiness(tmp_path):
    path = tmp_path/'ambiguous.sqlite3'
    initialize(path)
    client = TestClient(create_app(path,{'same':'fictional-owner'},['same']))
    assert client.get('/ready').status_code == 503


def test_missing_clustering_runtime_blocks_readiness(client, tmp_path, monkeypatch):
    initialize(tmp_path/'frontend.sqlite3')
    def unavailable(_):
        raise ImportError('Fictional missing dependency')
    monkeypatch.setattr(readiness,'import_module',unavailable)
    result = client.get('/ready')
    assert result.status_code == 503 and result.json()['checks']['clustering_runtime']['status'] == 'unavailable'


def test_optional_guidelines_and_predictors_do_not_claim_approval(tmp_path):
    path = tmp_path/'configured.sqlite3'
    initialize(path)
    client = TestClient(create_app(path,{},historical_predictor=object(),prospective_predictor=object(),
                                   planning_guideline_dir=tmp_path/'missing-guidelines'))
    result = client.get('/ready')
    assert result.status_code == 200
    checks = result.json()['checks']
    assert checks['guidelines']['status'] == 'missing'
    assert checks['historical_predictor']['status'] == checks['prospective_predictor']['status'] == 'configured_not_validated'


def test_response_models_preserve_existing_payloads_and_openapi(client):
    created = client.post(PATH,headers=OWNER,json=plan()).json()
    identifier = created['plan']['plan_id']
    assert client.get(PATH+'/'+identifier,headers=OWNER).json() == created
    workflow = client.get('/api/farmer-workflow/plans/'+identifier,headers=OWNER).json()
    assert workflow == {'plan':created['plan'],'personalized_plan':None}
    request = dict(plan_id=identifier,final_crop='Corn',district='Matara',region='north',land_size_acres=2,
                   planting_date='2030-01-01',expected_harvest_date='2030-04-01',season='Maha')
    generated = client.post('/api/personalized-cultivation-plans/generate',headers=OWNER,json=request)
    assert generated.status_code == 200 and generated.json()['activities'] == []
    assert 'cultivation_updated_at' not in generated.json()
    saved = client.post('/api/personalized-cultivation-plans/save',headers=OWNER,json=request)
    assert saved.status_code == 200 and 'cultivation_updated_at' in saved.json()['personalized_plan']
    assert client.get('/api/personalized-cultivation-plans/'+identifier,headers=OWNER).json() == saved.json()
    report = client.post('/api/farmer-workflow/analyze',headers=OWNER,json={'plan_id':identifier}).json()
    assert report['assessment']['risk_level'] is None and report['recommendations']['alternatives'] == []
    assert report['experimental_reference_assessment']['validation_status'] != 'validated'
    schema = client.get('/openapi.json').json()
    for path,method,model in ((PATH,'get','PlanListResponse'),('/ready','get','ReadinessResponse'),
                             ('/health','get','HealthResponse'),('/api/farmer-workflow/analyze','post','WorkflowReportResponse'),
                             ('/api/personalized-cultivation-plans/save','post','SavedPersonalizedPlanResponse')):
        contract = schema['paths'][path][method]['responses']['200']['content']['application/json']['schema']
        assert contract['$ref'].endswith('/'+model)
    assert {'200','401','422','503'} <= set(schema['paths'][PATH]['get']['responses'])
    assert schema['paths'][PATH]['get']['security']
    assert schema['paths']['/ready']['get']['responses']['503']['content']['application/json']['schema']['$ref'].endswith('/ReadinessResponse')
