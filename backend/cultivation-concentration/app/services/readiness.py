"""Dependency readiness only. Never load/activate a model or approve research evidence."""
import hashlib
import json
import sqlite3
from contextlib import closing
from importlib import import_module
from pathlib import Path
from fastapi import HTTPException
from app.migrations import MIGRATIONS
from app.services.farmer_auth import session_ttl

ROOT = Path(__file__).resolve().parents[2]
MODEL_CATALOG = ROOT / 'models/artifact_catalog.json'
GUIDELINE_FILE = ROOT / 'data/guidelines/v1.1/verified_entries.json'
REQUIRED_COLUMNS = {
    'cultivation_plans': 'plan_id,farmer_id,district,region,crop,land_size_acres,planting_date,expected_harvest_date,submitted_at,updated_at,status',
    'cultivation_plan_versions': 'version_id,plan_id,recorded_at,payload',
    'personalized_plan_versions': 'revision_id,plan_id,farmer_id,saved_at,payload',
    'farmer_accounts': 'farmer_id,login_identifier,password_hash,created_at,disabled',
    'farmer_sessions': 'token_digest,farmer_id,created_at,expires_at,revoked_at',
    'farmer_auth_throttles': 'bucket_digest,window_started_at,attempts',
}


def check(status, required, detail):
    return dict(status=status, required=required, detail=detail)


def database_check(database_path):
    path = Path(database_path).resolve()
    if not path.is_file():
        return check('not_initialized', True, 'Initialize the cultivation database and account migrations before serving traffic')
    try:
        # mode=rw refuses to create a missing database. Always roll back the write probe.
        with closing(sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=0.2)) as db:
            try:
                for table, columns in REQUIRED_COLUMNS.items():
                    db.execute('SELECT ' + columns + ' FROM ' + table + ' LIMIT 0')
                versions = dict(db.execute('SELECT version,name FROM component02_schema_migrations'))
                if any(versions.get(version) != name for version, name in MIGRATIONS):
                    return check('not_initialized', True, 'Required account migrations have not been applied')
                db.execute('BEGIN IMMEDIATE')
                db.execute('UPDATE component02_schema_migrations SET applied_at=applied_at WHERE 0')
            finally:
                db.rollback()
        return check('ready', True, 'Required schema, migration ledger and database write access are available')
    except (sqlite3.Error, OSError, ValueError):
        return check('unavailable', True, 'Database unavailable, busy, read-only or required schema missing')


def model_artifacts_check():
    if not MODEL_CATALOG.is_file():
        return check('missing', False, 'Optional research artifact catalog is missing; no model validation asserted')
    try:
        catalog = json.loads(MODEL_CATALOG.read_text(encoding='utf-8'))
        names = [name for name in catalog['files'] if name.endswith('.joblib')]
        root = MODEL_CATALOG.parent.parent.resolve()
        paths = [(root / name).resolve() for name in names]
        if not names or any(not path.is_relative_to(root) for path in paths):
            raise ValueError('Invalid catalog')
        if any(not path.is_file() for path in paths):
            return check('missing', False, 'Optional catalogued model artifacts are missing; no model validation asserted')
        return check('present_not_validated', False, 'File presence only; hashes, predictions and agricultural validity are not checked by readiness')
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return check('unavailable', False, 'Optional research artifact metadata is unavailable; no model validation asserted')


def report(database_path, roles, legacy_enabled, historical_predictor=None, prospective_predictor=None,
           planning_guideline_dir=None):
    checks = {'database': database_check(database_path)}
    try:
        roles()
        session_ttl()
        if legacy_enabled not in ('true', 'false'):
            raise ValueError('Invalid compatibility setting')
        if not hasattr(hashlib, 'scrypt'):
            raise ValueError('Password hashing unavailable')
        checks['authentication'] = check('ready', True, 'Account sessions and research role configuration are available')
    except (HTTPException, ValueError, TypeError):
        checks['authentication'] = check('unavailable', True, 'Authentication configuration or password hashing support is unavailable')
    try:
        import_module('app.services.plan_clustering')
        checks['clustering_runtime'] = check('ready', True, 'Clustering dependencies import successfully; no predictions or agricultural validation asserted')
    except (ImportError, OSError, RuntimeError, ValueError):
        checks['clustering_runtime'] = check('unavailable', True, 'Required clustering dependencies cannot be imported')
    guideline = Path(planning_guideline_dir) / 'verified_entries.json' if planning_guideline_dir else GUIDELINE_FILE
    try:
        entries = json.loads(guideline.read_text(encoding='utf-8'))['entries']
        if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
            raise ValueError('Invalid guideline document')
        checks['guidelines'] = check('available_not_approved', False, 'Guideline document is readable; applicable claim approvals are still required')
    except FileNotFoundError:
        checks['guidelines'] = check('missing', False, 'Planning guideline document is missing; planning may be unavailable')
    except (OSError, ValueError, TypeError, KeyError):
        checks['guidelines'] = check('unavailable', False, 'Planning guideline document is invalid or unavailable')
    checks['model_artifacts'] = model_artifacts_check()
    for name, predictor in (('historical_predictor', historical_predictor), ('prospective_predictor', prospective_predictor)):
        checks[name] = check('not_configured' if predictor is None else 'configured_not_validated', False,
                             'Optional predictor configuration only; no research validity or prediction availability asserted')
    ready = all(value['status'] == 'ready' for value in checks.values() if value['required'])
    return dict(status='ready' if ready else 'not_ready', checks=checks, research_validation='not_asserted')
