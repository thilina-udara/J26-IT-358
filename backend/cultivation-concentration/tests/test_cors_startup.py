"""Run the real app constructor and middleware in a process without pytest flags."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPT = r'''
import json,os,sys
assert 'PYTEST_CURRENT_TEST' not in os.environ
from fastapi.testclient import TestClient
from app.main import create_app
from app.cors import allowed_origins
client=TestClient(create_app(sys.argv[1],{},[]))
result={'configured':allowed_origins(),'origins':{}}
for origin in ['http://localhost:3000','http://127.0.0.1:3000','http://localhost:3001','http://127.0.0.1:3005','https://example.invalid']:
 response=client.options('/api/cultivation-plans',headers={'Origin':origin,'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'})
 result['origins'][origin]={'status':response.status_code,'allowed':response.headers.get('access-control-allow-origin'),'credentials':response.headers.get('access-control-allow-credentials')}
private=client.options('/api/cultivation-plans',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'GET','Access-Control-Request-Private-Network':'true'})
result['private_network']=private.headers.get('access-control-allow-private-network')
print(json.dumps(result))
'''


@pytest.mark.parametrize("origins", [[], ["http://localhost:3000", "http://127.0.0.1:3000"]])
def test_actual_startup_uses_only_explicit_origins_outside_pytest(tmp_path, origins):
    environment = dict(os.environ, CULTIVATION_CORS_ORIGINS=json.dumps(origins), CULTIVATION_HISTORICAL_MODEL="")
    environment.pop("PYTEST_CURRENT_TEST", None)
    result = subprocess.run([sys.executable, "-c", SCRIPT, str(tmp_path / "startup.sqlite3")],
                            cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    assert data["configured"] == origins
    for origin, response in data["origins"].items():
        assert response["status"] == (200 if origin in origins else 400)
        assert response["allowed"] == (origin if origin in origins else None)
        assert response["credentials"] is None
    assert data["private_network"] is None


def test_absent_configuration_never_grants_development_origins_outside_pytest():
    environment = dict(os.environ)
    for key in ("PYTEST_CURRENT_TEST", "CULTIVATION_CORS_ORIGINS"):
        environment.pop(key, None)
    script = "from app.cors import allowed_origins; assert allowed_origins() == []"
    subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1], env=environment, check=True)
