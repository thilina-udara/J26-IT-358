"""Run this copy's SQLite-only PP1 services with fixed local resources."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend/cultivation-concentration'
STORAGE = BACKEND / 'storage/pp1'
DATABASE = STORAGE / 'cultivation_plans.sqlite3'
PYTHON = ROOT / '.venv/Scripts/python.exe'
API = 'http://127.0.0.1:8001'


def environment():
    # Ignore inherited application, Python and connection overrides.
    prefixes = ('CULTIVATION_', 'POSTGRES_', 'REDIS_', 'CELERY_', 'NEXT_PUBLIC_')
    blocked = {'DATABASE_URL', 'PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'NODE_OPTIONS', 'PORT'}
    env = {k: v for k, v in os.environ.items()
           if k.upper() not in blocked and not k.upper().startswith(prefixes)}
    node = shutil.which('node.exe')
    env['PATH'] = os.pathsep.join(filter(None, [str(PYTHON.parent),
        str(Path(node).parent) if node else None,
        str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32')]))
    temporary = ROOT / 'scratch/pp1-isolation/tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    env.update({
        'VIRTUAL_ENV': str(ROOT / '.venv'),
        'TEMP': str(temporary), 'TMP': str(temporary),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'NEXT_TELEMETRY_DISABLED': '1',
        'NEXT_PUBLIC_CULTIVATION_API_URL': API,
        'DATABASE_URL': 'sqlite:///' + DATABASE.as_posix(),
        'REDIS_URL': '', 'CELERY_BROKER_URL': '', 'CELERY_RESULT_BACKEND': '',
        'CULTIVATION_PLAN_DB': str(DATABASE),
        'CULTIVATION_REFERENCE_DB': str(STORAGE / 'reference_governance.sqlite3'),
        'CULTIVATION_RESEARCH_DEMO_DB': str(STORAGE / 'research_demo.sqlite3'),
        'CULTIVATION_CORS_ORIGINS': '["http://127.0.0.1:3001","http://localhost:3001"]',
        'CULTIVATION_LEGACY_FARMER_TOKENS_ENABLED': 'false',
        'CULTIVATION_FARMER_TOKENS': '{}', 'CULTIVATION_ADMIN_TOKENS': '[]',
        'CULTIVATION_ANALYSIS_TOKENS': '[]', 'CULTIVATION_REVIEWER_TOKENS': '{}',
        'CULTIVATION_RESEARCH_DEMO_ENABLED': 'true',
        'CULTIVATION_HISTORICAL_MODEL': '',
    })
    return env


def preflight():
    expected = Path('D:/meeting/J26-IT-358').resolve()
    if ROOT != expected or Path(sys.prefix).resolve() != (ROOT / '.venv').resolve():
        raise SystemExit('Use this copy\'s .venv/Scripts/python.exe to run scripts/pp1.py.')
    for path in (ROOT / '.venv', BACKEND, STORAGE, ROOT / 'frontend'):
        for parent in (path, *path.parents):
            if parent.is_symlink() or parent.is_junction():
                raise SystemExit(f'PP1 path must not contain a link: {parent}')
            if parent == ROOT:
                break
        if not path.resolve().is_relative_to(ROOT):
            raise SystemExit(f'PP1 path escapes this copy: {path}')
    STORAGE.mkdir(parents=True, exist_ok=True)
    for path in (DATABASE, STORAGE / 'reference_governance.sqlite3', STORAGE / 'research_demo.sqlite3'):
        if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
            raise SystemExit(f'PP1 database must be an independent file: {path}')


def require_free_port(port):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service', choices=('backend', 'frontend', 'init-db', 'info'))
    service = parser.parse_args().service
    preflight()
    env = environment()
    if service == 'info':
        print(json.dumps({'python': str(PYTHON), 'database': str(DATABASE),
            'frontend': 'http://127.0.0.1:3001', 'backend': API}, indent=2))
        return
    if service == 'init-db':
        command = [str(PYTHON), '-I', '-B', '-c',
            'import sys; sys.path.insert(0, sys.argv.pop(1)); from app.migrations.__main__ import main; main()',
            str(BACKEND), '--database', str(DATABASE)]
        cwd = BACKEND
    elif service == 'backend':
        if not DATABASE.is_file():
            raise SystemExit('Initialize this copy\'s database first: scripts/pp1.py init-db')
        require_free_port(8001)
        command = [str(PYTHON), '-I', '-B', '-m', 'uvicorn', 'app.main:app',
            '--app-dir', str(BACKEND), '--host', '127.0.0.1', '--port', '8001']
        cwd = BACKEND
    else:
        require_free_port(3001)
        node = shutil.which('node.exe', path=env['PATH'])
        if not node:
            raise SystemExit('Node.js is not available.')
        cwd = ROOT / 'frontend'
        command = [node, str(cwd / 'node_modules/next/dist/bin/next'),
            'dev', '--hostname', '127.0.0.1', '--port', '3001']
    raise SystemExit(subprocess.call(command, cwd=cwd, env=env))


if __name__ == '__main__':
    main()
