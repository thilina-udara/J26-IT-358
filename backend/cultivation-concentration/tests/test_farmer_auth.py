"""Fictional accounts only; authentication never relies on real farmer records."""
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.migrations import migrate, MIGRATIONS
from app.schemas.auth import RegisterInput
from app.schemas.cultivation_plan import PlanInput
from app.services import farmer_auth
from app.services.cultivation_plans import PlanStore
from app.services.farmer_auth import AuthStore

PASSWORD = 'Fictional password for testing 02!'


def headers(token):
    return {'Authorization': 'Bearer ' + token}


def account(client, identifier='fictional-alice'):
    value = dict(login_identifier=identifier, password=PASSWORD)
    registered = client.post('/auth/register', json=value)
    assert registered.status_code == 201, registered.text
    logged = client.post('/auth/login', json=value)
    assert logged.status_code == 200, logged.text
    return registered.json(), logged.json()


def plan(**changes):
    return dict(dict(district='Matara', region='north', crop='Corn', land_size_acres=2,
                     planting_date='2030-01-01', expected_harvest_date='2030-04-01'), **changes)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED', 'true')
    monkeypatch.setenv('CULTIVATION_SESSION_TTL_SECONDS', '3600')
    return TestClient(create_app(tmp_path / 'fictional.sqlite3', {}, [], admin_tokens=[], reviewer_tokens={}))


def test_registration_login_me_and_no_raw_credentials_at_rest(client, tmp_path):
    registered, session = account(client)
    assert registered['farmer_id'].startswith('farmer-')
    assert registered['login_identifier'] == 'fictional-alice'
    assert 'password' not in registered and 'password_hash' not in registered
    assert session['expires_in'] == 3600 and session['token_type'] == 'bearer'
    assert datetime.fromisoformat(session['expires_at']).tzinfo is not None
    response = client.get('/auth/me', headers=headers(session['access_token']))
    assert response.status_code == 200 and response.json() == registered
    assert response.headers['cache-control'] == 'no-store'
    with sqlite3.connect(tmp_path / 'fictional.sqlite3') as db:
        hashed = db.execute('SELECT password_hash FROM farmer_accounts').fetchone()[0]
        stored = db.execute('SELECT token_digest FROM farmer_sessions').fetchone()[0]
        dump = '\n'.join(db.iterdump())
    assert hashed.startswith('scrypt$131072$8$1$')
    assert stored == hashlib.sha256(session['access_token'].encode()).hexdigest()
    assert session['access_token'] not in dump and PASSWORD not in dump


def test_duplicate_normalized_registration(client):
    first = client.post('/auth/register', json=dict(login_identifier=' Fictional.Alice ', password=PASSWORD))
    assert first.status_code == 201 and first.json()['login_identifier'] == 'fictional.alice'
    duplicate = client.post('/auth/register', json=dict(login_identifier='FICTIONAL.ALICE', password=PASSWORD))
    assert duplicate.status_code == 409
    login = client.post('/auth/login', json=dict(login_identifier=' Fictional.Alice ', password=PASSWORD))
    assert login.status_code == 200 and login.json()['farmer']['farmer_id'] == first.json()['farmer_id']


def test_invalid_login_is_generic_and_does_not_create_sessions(client, tmp_path):
    registered, _ = account(client)
    wrong = client.post('/auth/login', json=dict(login_identifier='fictional-alice', password='wrong'))
    unknown = client.post('/auth/login', json=dict(login_identifier='fictional-unknown', password='wrong'))
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.headers['www-authenticate'] == 'Bearer'
    with sqlite3.connect(tmp_path / 'fictional.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM farmer_sessions').fetchone()[0] == 1
        assert db.execute('SELECT farmer_id FROM farmer_accounts').fetchone()[0] == registered['farmer_id']


@pytest.mark.parametrize('changes', [
    {'password': 'short-secret'}, {'password': 'x' * 129}, {'login_identifier': 'bad space'},
    {'login_identifier': 'ééé'}, {'login_identifier': '   '}, {'farmer_id': 'chosen-id'},
    {'role': 'administrator'},
])
def test_invalid_registration_redacts_password(client, changes):
    value = dict(login_identifier='fictional-test', password=PASSWORD)
    value.update(changes)
    response = client.post('/auth/register', json=value)
    assert response.status_code == 422
    assert value['password'] not in response.text
    assert response.headers['cache-control'] == 'no-store'


def test_password_whitespace_is_preserved(client):
    value = dict(login_identifier='fictional-spaces', password='  Fictional long password  ')
    assert client.post('/auth/register', json=value).status_code == 201
    assert client.post('/auth/login', json=value).status_code == 200
    assert client.post('/auth/login', json=dict(value, password=value['password'].strip())).status_code == 401


def test_expiry_boundary_rejects_all_farmer_routes(client, monkeypatch):
    clock = [2_000_000_000]
    monkeypatch.setattr(farmer_auth, 'now_seconds', lambda: clock[0])
    _, session = account(client)
    token = headers(session['access_token'])
    clock[0] += 3599
    assert client.get('/auth/me', headers=token).status_code == 200
    clock[0] += 1
    assert client.get('/auth/me', headers=token).status_code == 401
    assert client.post('/api/cultivation-plans', headers=token, json=plan()).status_code == 401
    assert client.post('/auth/logout', headers=token).status_code == 401


def test_logout_revokes_only_current_session_and_survives_restart(client, tmp_path):
    _, first = account(client)
    second = client.post('/auth/login', json=dict(login_identifier='fictional-alice', password=PASSWORD)).json()
    assert first['access_token'] != second['access_token']
    response = client.post('/auth/logout', headers=headers(first['access_token']))
    assert response.status_code == 204 and response.content == b''
    reopened = TestClient(create_app(tmp_path / 'fictional.sqlite3', {}))
    assert reopened.get('/auth/me', headers=headers(first['access_token'])).status_code == 401
    assert reopened.get('/auth/me', headers=headers(second['access_token'])).status_code == 200
    assert reopened.post('/auth/logout', headers=headers(first['access_token'])).status_code == 401


def test_revoked_session_never_falls_back_to_research_registry(client, tmp_path):
    _, session = account(client)
    token = session['access_token']
    assert client.post('/auth/logout', headers=headers(token)).status_code == 204
    reopened = TestClient(create_app(tmp_path / 'fictional.sqlite3', {token: 'fictional-legacy'}))
    assert reopened.get('/auth/me', headers=headers(token)).status_code == 401
    assert reopened.post('/api/cultivation-plans', headers=headers(token), json=plan()).status_code == 401


@pytest.mark.parametrize('token', [None, 'invalid', 'cc_session_malformed', 'cc_session_' + 'x' * 43])
def test_unauthorized_access(client, token):
    auth = headers(token) if token else {}
    for path in ('/auth/me', '/api/cultivation-plans/missing'):
        assert client.get(path, headers=auth).status_code == 401
    assert client.post('/auth/logout', headers=auth).status_code == 401
    assert client.post('/api/cultivation-plans', headers=auth, json=plan()).status_code == 401


def test_identity_ownership_privacy_and_persistence(client, tmp_path):
    alice, alice_session = account(client)
    bob, bob_session = account(client, 'fictional-bob')
    ah, bh = headers(alice_session['access_token']), headers(bob_session['access_token'])
    created = client.post('/api/cultivation-plans', headers=ah, json=plan())
    assert created.status_code == 201
    assert created.json()['plan']['farmer_id'] == alice['farmer_id']
    assert created.json()['concentration']['total_acreage'] is None
    endpoint = '/api/cultivation-plans/' + created.json()['plan']['plan_id']
    assert client.post('/api/cultivation-plans', headers=ah, json=plan(farmer_id=bob['farmer_id'])).status_code == 403
    assert client.put(endpoint, headers=ah, json=plan(farmer_id=bob['farmer_id'])).status_code == 403
    for method in ('get', 'put', 'delete'):
        response = getattr(client, method)(endpoint, headers=bh, **({'json': plan()} if method == 'put' else {}))
        assert response.status_code == 404
    assert client.get(endpoint + '/risk-assessment', headers=bh, params={'season': 'Maha'}).status_code == 404
    assert client.post('/api/farmer-workflow/analyze', headers=bh,
                       json={'plan_id': created.json()['plan']['plan_id']}).status_code == 404
    assert client.put(endpoint, headers=ah, json=plan(land_size_acres=3)).status_code == 200
    restarted = TestClient(create_app(tmp_path / 'fictional.sqlite3', {}))
    assert restarted.get(endpoint, headers=ah).json()['plan']['land_size_acres'] == 3
    login = restarted.post('/auth/login', json=dict(login_identifier='fictional-alice', password=PASSWORD))
    assert login.status_code == 200 and login.json()['farmer']['farmer_id'] == alice['farmer_id']


def test_workflow_derives_account_identity(client):
    farmer, session = account(client)
    response = client.post('/api/farmer-workflow/plans', headers=headers(session['access_token']), json=plan())
    assert response.status_code == 201
    assert response.json()['plan']['farmer_id'] == farmer['farmer_id']
    assert response.json()['workflow']['assessment']['risk_level'] is None
    assert response.json()['workflow']['recommendations']['alternatives'] == []


def test_existing_research_users_and_roles_remain_separate(tmp_path, monkeypatch):
    monkeypatch.setenv('CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED', 'true')
    client = TestClient(create_app(tmp_path / 'roles.sqlite3', {'research': 'fictional-legacy'}, ['analyst'],
                                   admin_tokens=['admin'], reviewer_tokens={'reviewer': 'expert'}))
    created = client.post('/api/cultivation-plans', headers=headers('research'), json=plan(farmer_id='fictional-legacy'))
    assert created.status_code == 201
    me = client.get('/auth/me', headers=headers('research'))
    assert me.json()['farmer_id'] == 'fictional-legacy'
    assert me.json()['authentication_method'] == 'legacy_research_token'
    assert client.post('/auth/logout', headers=headers('research')).status_code == 401
    farmer, session = account(client)
    for token in ('analyst', 'admin'):
        assert client.get('/api/cultivation-analysis/clusters', headers=headers(token), params={'district': 'Matara'}).status_code == 200
        assert client.get('/auth/me', headers=headers(token)).status_code == 401
    # A recognized reviewer reaches assignment checking rather than credential denial.
    case = '/api/expert-validation/cases/missing'
    params = dict(case_version=1, rubric_version='fictional-v1')
    review = client.get(case, headers=headers('reviewer'), params=params)
    assert review.status_code == 403 and review.json()['detail'] == 'Review assignment required'
    for token in ('research', session['access_token']):
        assert client.get('/api/cultivation-analysis/clusters', headers=headers(token), params={'district': 'Matara'}).status_code == 403
        assert client.get(case, headers=headers(token), params=params).status_code == 403
    assert client.get('/api/cultivation-plans/' + created.json()['plan']['plan_id'],
                      headers=headers(session['access_token'])).status_code == 404
    monkeypatch.setenv('CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED', 'false')
    assert client.get('/auth/me', headers=headers('research')).status_code == 401
    assert client.get('/auth/me', headers=headers(session['access_token'])).json()['farmer_id'] == farmer['farmer_id']


def test_migration_preserves_existing_plans_and_history(tmp_path):
    path = tmp_path / 'legacy.sqlite3'
    repository = PlanStore(path)
    first = repository.save(PlanInput(**plan(farmer_id='fictional-legacy')), 'fictional-legacy')['plan']
    repository.save(PlanInput(**plan(farmer_id='fictional-legacy', land_size_acres=3)),
                    'fictional-legacy', first.plan_id, personalized={'status': 'fictional-test'})
    tables = ('cultivation_plans', 'cultivation_plan_versions', 'personalized_plan_versions')
    with repository.connection() as db:
        before = {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)] for table in tables}
    migrate(path)
    migrate(path)
    with repository.connection() as db:
        after = {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)] for table in tables}
        assert db.execute('SELECT COUNT(*) FROM component02_schema_migrations').fetchone()[0] == len(MIGRATIONS)
        assert db.execute('SELECT COUNT(*) FROM farmer_accounts').fetchone()[0] == 0
    assert after == before
    client = TestClient(create_app(path, {'research': 'fictional-legacy'}))
    assert client.get('/api/cultivation-plans/' + first.plan_id, headers=headers('research')).status_code == 200


def test_migration_is_atomic_on_conflicting_schema(tmp_path):
    path = tmp_path / 'conflicting.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE farmer_sessions(existing TEXT)')
    with pytest.raises(sqlite3.OperationalError):
        migrate(path)
    with sqlite3.connect(path) as db:
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert names == {'farmer_sessions'}


def test_duplicate_registration_race_is_database_enforced(tmp_path):
    path = tmp_path / 'race.sqlite3'
    repository = AuthStore(path)
    value = RegisterInput(login_identifier='fictional-race', password=PASSWORD)
    def register():
        try:
            repository.register(value)
            return 201
        except farmer_auth.HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: register(), range(2)))
    assert sorted(statuses) == [201, 409]


def test_same_password_has_unique_salts(client, tmp_path):
    for identifier in ('fictional-one', 'fictional-two'):
        assert client.post('/auth/register', json=dict(login_identifier=identifier, password=PASSWORD)).status_code == 201
    with sqlite3.connect(tmp_path / 'fictional.sqlite3') as db:
        hashes = [r[0] for r in db.execute('SELECT password_hash FROM farmer_accounts')]
    assert hashes[0] != hashes[1]


def test_disabled_account_cannot_login_or_use_existing_session(client, tmp_path):
    farmer, session = account(client)
    with sqlite3.connect(tmp_path / 'fictional.sqlite3') as db:
        db.execute('UPDATE farmer_accounts SET disabled=1 WHERE farmer_id=?', (farmer['farmer_id'],))
    assert client.get('/auth/me', headers=headers(session['access_token'])).status_code == 401
    assert client.post('/auth/login', json=dict(login_identifier='fictional-alice', password=PASSWORD)).status_code == 401


def test_login_throttle_persists_and_expires(client, tmp_path, monkeypatch):
    clock = [2_000_000_000]
    monkeypatch.setattr(farmer_auth, 'now_seconds', lambda: clock[0])
    value = dict(login_identifier='fictional-limited', password=PASSWORD)
    assert client.post('/auth/register', json=value).status_code == 201
    for _ in range(5):
        assert client.post('/auth/login', json=dict(value, password='wrong')).status_code == 401
    restarted = TestClient(create_app(tmp_path / 'fictional.sqlite3', {}))
    limited = restarted.post('/auth/login', json=value)
    assert limited.status_code == 429 and int(limited.headers['retry-after']) == 900
    clock[0] += 900
    assert restarted.post('/auth/login', json=value).status_code == 200


def test_client_throttle_blocks_registration_before_hashing(client, tmp_path, monkeypatch):
    AuthStore(tmp_path / 'fictional.sqlite3').reserve_attempt('client', 'testclient', 40)
    with sqlite3.connect(tmp_path / 'fictional.sqlite3') as db:
        db.execute('UPDATE farmer_auth_throttles SET attempts=40')
    def unexpected_hash(_):
        raise AssertionError('Throttled registration must not hash a password')
    monkeypatch.setattr(farmer_auth, 'hash_password', unexpected_hash)
    response = client.post('/auth/register', json=dict(login_identifier='fictional-limit', password=PASSWORD))
    assert response.status_code == 429


@pytest.mark.parametrize('ttl', ['0', '-1', '86401', 'invalid'])
def test_invalid_session_configuration_fails_closed(client, monkeypatch, ttl):
    value = dict(login_identifier='fictional-config', password=PASSWORD)
    assert client.post('/auth/register', json=value).status_code == 201
    monkeypatch.setenv('CULTIVATION_SESSION_TTL_SECONDS', ttl)
    assert client.post('/auth/login', json=value).status_code == 503


def test_custom_session_expiry(client, monkeypatch):
    monkeypatch.setenv('CULTIVATION_SESSION_TTL_SECONDS', '120')
    _, session = account(client)
    assert session['expires_in'] == 120


def test_openapi_contract_and_health_remain_lazy(tmp_path):
    path = tmp_path / 'not-created.sqlite3'
    client = TestClient(create_app(path, {}))
    assert client.get('/health').status_code == 200
    schema = client.get('/openapi.json').json()
    assert all('/auth/' + path in schema['paths'] for path in ('register', 'login', 'me', 'logout'))
    assert 'farmer_id' not in schema['components']['schemas']['PlanSubmission']['required']
    assert schema['components']['schemas']['RegisterInput']['properties']['password']['writeOnly']
    assert not path.exists()


def test_password_hash_work_is_bounded(client):
    assert farmer_auth.PASSWORD_WORK.acquire(blocking=False)
    assert farmer_auth.PASSWORD_WORK.acquire(blocking=False)
    try:
        response = client.post('/auth/register', json=dict(login_identifier='fictional-busy', password=PASSWORD))
        assert response.status_code == 503 and response.headers['retry-after'] == '1'
        assert PASSWORD not in response.text
    finally:
        farmer_auth.PASSWORD_WORK.release()
        farmer_auth.PASSWORD_WORK.release()
