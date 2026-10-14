import asyncio
import json
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.core.config import normalize_database_url, settings
from app.core.database import engine, get_db
from app.main import app, root, health_check, database_health_check


async def asgi_request(asgi_app, method: str, path: str):
    """Helper to dispatch ASGI requests directly through FastAPI without external HTTP clients."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [(b"host", b"localhost")],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
    }
    status_code = None
    response_headers = []
    body_parts = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code, response_headers, body_parts
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))

    await asgi_app(scope, receive, send)
    body = b"".join(body_parts).decode("utf-8")
    parsed_body = json.loads(body) if body else {}
    return status_code, parsed_body


class TestDatabaseConfiguration(unittest.TestCase):
    def test_normalize_postgresql_prefix(self):
        raw = "postgresql://user:pass123@localhost:5432/agri_db"
        expected = "postgresql+psycopg2://user:pass123@localhost:5432/agri_db"
        self.assertEqual(normalize_database_url(raw), expected)

    def test_normalize_postgres_prefix(self):
        raw = "postgres://user:pass123@localhost:5432/agri_db"
        expected = "postgresql+psycopg2://user:pass123@localhost:5432/agri_db"
        self.assertEqual(normalize_database_url(raw), expected)

    def test_normalize_already_normalized(self):
        raw = "postgresql+psycopg2://user:pass123@localhost:5432/agri_db"
        self.assertEqual(normalize_database_url(raw), raw)

    def test_normalize_preserves_complex_credentials(self):
        raw = "postgresql://user_test:p@$$:w0rd!@127.0.0.1:5432/db_test"
        normalized = normalize_database_url(raw)
        self.assertTrue(normalized.startswith("postgresql+psycopg2://"))
        self.assertIn("user_test:p@$$:w0rd!", normalized)

    def test_get_database_url_uses_psycopg2(self):
        db_url = settings.get_database_url()
        self.assertTrue(
            db_url.startswith("postgresql+psycopg2://"),
            f"Expected URL to start with postgresql+psycopg2://, got {db_url[:25]}..."
        )


class TestHealthEndpoints(unittest.TestCase):
    def test_root_endpoint(self):
        status_code, body = asyncio.run(asgi_request(app, "GET", "/"))
        self.assertEqual(status_code, 200)
        self.assertEqual(body.get("status"), "online")
        self.assertEqual(body.get("port"), 8001)

    def test_existing_health_endpoint(self):
        status_code, body = asyncio.run(asgi_request(app, "GET", "/health"))
        self.assertEqual(status_code, 200)
        self.assertEqual(body.get("status"), "healthy")
        self.assertEqual(body.get("service"), "market-profit-service")

    def test_database_health_endpoint_success(self):
        status_code, body = asyncio.run(asgi_request(app, "GET", "/health/db"))
        self.assertEqual(status_code, 200)
        self.assertEqual(body.get("status"), "healthy")
        self.assertEqual(body.get("database"), "connected")

    @patch("app.main.engine.connect")
    def test_database_health_endpoint_failure_handles_gracefully(self, mock_connect):
        mock_connect.side_effect = Exception("Simulated DB connection failure")
        status_code, body = asyncio.run(asgi_request(app, "GET", "/health/db"))
        self.assertEqual(status_code, 503)
        self.assertEqual(body.get("detail"), "Database connection unavailable")
        self.assertNotIn("Simulated DB connection failure", str(body))
        self.assertNotIn("postgresql", str(body))

    def test_get_db_session_lifecycle(self):
        gen = get_db()
        session = next(gen)
        self.assertIsNotNone(session)
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    unittest.main()
