import asyncio
import json
import unittest
from datetime import date
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app


class TestSecurityAndAccessControl(unittest.TestCase):
    """
    Comprehensive test suite verifying security controls and access restrictions:
    - Fail-closed behavior when server administrator key is unconfigured (Task 1)
    - Rejection of unprotected DELETE calls across all entities (401 Unauthorized)
    - Rejection of unprotected historical market data writes (401 Unauthorized)
    - Protection of farmer cultivation budgets and profit analyses from unauthenticated retrieval (Task 2)
    - Rejection of invalid credentials with 403 Forbidden
    - Acceptance of temporary test-only credentials (primary X-Admin-Key and secondary X-API-Key)
    - Preservation of unauthenticated public access for price/demand exploration and farmer calculation requests
    - Verification of OpenAPI security definitions
    """

    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        app.dependency_overrides[get_db] = lambda: self.session

        # Use temporary, isolated test-only credentials (never hardcoded in application code)
        self.test_admin_key = "test-isolated-security-key-temp"
        self.original_admin_key = settings.ADMIN_API_KEY
        settings.ADMIN_API_KEY = self.test_admin_key

    def tearDown(self):
        settings.ADMIN_API_KEY = self.original_admin_key
        app.dependency_overrides.clear()
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    def dispatch_request(self, method: str, path: str, body: dict = None, headers: dict = None):
        """Dispatch ASGI request directly through FastAPI application."""
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        req_headers = [(b"host", b"localhost")]
        if body is not None:
            req_headers.append((b"content-type", b"application/json"))
        if headers:
            for k, v in headers.items():
                req_headers.append((k.lower().encode("utf-8"), v.encode("utf-8")))

        status_code = None
        response_headers = []
        body_parts = []

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": req_headers,
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 80),
        }

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        async def send(message):
            nonlocal status_code, response_headers
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        asyncio.run(app(scope, receive, send))
        response_text = b"".join(body_parts).decode("utf-8")
        parsed_body = json.loads(response_text) if response_text else None
        header_dict = {k.decode("utf-8").lower(): v.decode("utf-8") for k, v in response_headers}
        return status_code, parsed_body, header_dict

    # -------------------------------------------------------------------------
    # 1. Fail-Closed When Admin Key is Unconfigured (Task 1)
    # -------------------------------------------------------------------------

    def test_unconfigured_admin_key_fails_closed(self):
        """When ADMIN_API_KEY is None, protected endpoints must fail closed and reject requests."""
        settings.ADMIN_API_KEY = None
        status_code, body, _ = self.dispatch_request(
            "DELETE",
            "/api/v1/market-prices/1",
            headers={"X-Admin-Key": "any-attempted-key"}
        )
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative access is unavailable", body["detail"])

    def test_empty_string_admin_key_fails_closed(self):
        """When ADMIN_API_KEY is empty or whitespace, protected endpoints must fail closed."""
        settings.ADMIN_API_KEY = "   "
        status_code, body, _ = self.dispatch_request(
            "DELETE",
            "/api/v1/market-prices/1",
            headers={"X-Admin-Key": "any-attempted-key"}
        )
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative access is unavailable", body["detail"])

    # -------------------------------------------------------------------------
    # 2. Unprotected Historical Data Writes (Must Return 401)
    # -------------------------------------------------------------------------

    def test_unprotected_create_market_price_rejected_401(self):
        payload = {
            "crop_id": "CR_TOMATO",
            "market_id": "DEC_DAMBULLA",
            "market_name": "Dambulla DEC",
            "district_id": "LK-22",
            "price_date": "2026-10-15",
            "price_type": "wholesale",
            "price": 180.00,
            "data_source": "HARTI"
        }
        status_code, body, headers = self.dispatch_request("POST", "/api/v1/market-prices", body=payload)
        self.assertEqual(status_code, 401)
        self.assertIn("www-authenticate", headers)
        self.assertIn("Administrative authorization required", body["detail"])

    def test_unprotected_create_market_demand_rejected_401(self):
        payload = {
            "crop_id": "CR_CHILLI",
            "district_id": "LK-71",
            "period_start_date": "2026-10-01",
            "period_end_date": "2026-10-07",
            "demand_volume_kg": 10000.0,
            "record_type": "observed",
            "data_source": "Field Survey"
        }
        status_code, body, headers = self.dispatch_request("POST", "/api/v1/market-demands", body=payload)
        self.assertEqual(status_code, 401)
        self.assertIn("www-authenticate", headers)
        self.assertIn("Administrative authorization required", body["detail"])

    # -------------------------------------------------------------------------
    # 3. Unprotected DELETE Operations (Must Return 401)
    # -------------------------------------------------------------------------

    def test_unprotected_delete_market_price_rejected_401(self):
        status_code, body, headers = self.dispatch_request("DELETE", "/api/v1/market-prices/1")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    def test_unprotected_delete_market_demand_rejected_401(self):
        status_code, body, headers = self.dispatch_request("DELETE", "/api/v1/market-demands/1")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    def test_unprotected_delete_cultivation_budget_rejected_401(self):
        status_code, body, headers = self.dispatch_request("DELETE", "/api/v1/cultivation-budgets/1")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    def test_unprotected_delete_profit_analysis_rejected_401(self):
        status_code, body, headers = self.dispatch_request("DELETE", "/api/v1/profit-analyses/REF-TEST123456")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    # -------------------------------------------------------------------------
    # 4. Protection of Farmer Data Retrieval (Task 2)
    # -------------------------------------------------------------------------

    def test_unprotected_list_cultivation_budgets_rejected_401(self):
        """Unauthenticated clients must be prevented from listing farmers' cultivation budgets."""
        status_code, body, headers = self.dispatch_request("GET", "/api/v1/cultivation-budgets")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    def test_unprotected_get_single_cultivation_budget_rejected_401(self):
        """Unauthenticated clients must be prevented from inspecting single farmer budget records."""
        status_code, body, headers = self.dispatch_request("GET", "/api/v1/cultivation-budgets/1")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    def test_unprotected_list_profit_analyses_rejected_401(self):
        """Unauthenticated clients must be prevented from listing saved farmer profit assessments."""
        status_code, body, headers = self.dispatch_request("GET", "/api/v1/profit-analyses")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    def test_unprotected_get_single_profit_analysis_rejected_401(self):
        """Unauthenticated clients must be prevented from looking up saved farmer profit analysis records."""
        status_code, body, headers = self.dispatch_request("GET", "/api/v1/profit-analyses/REF-TEST123456")
        self.assertEqual(status_code, 401)
        self.assertIn("Administrative authorization required", body["detail"])

    # -------------------------------------------------------------------------
    # 5. Invalid Credentials (Must Return 403 Forbidden)
    # -------------------------------------------------------------------------

    def test_invalid_admin_key_rejected_403(self):
        invalid_headers = {"X-Admin-Key": "completely-invalid-attacker-key"}
        status_code, body, _ = self.dispatch_request(
            "DELETE",
            "/api/v1/market-prices/1",
            headers=invalid_headers
        )
        self.assertEqual(status_code, 403)
        self.assertIn("Invalid administrative credentials", body["detail"])

    def test_invalid_api_key_secondary_header_rejected_403(self):
        invalid_headers = {"X-API-Key": "wrong-secret-token"}
        status_code, body, _ = self.dispatch_request(
            "GET",
            "/api/v1/cultivation-budgets/1",
            headers=invalid_headers
        )
        self.assertEqual(status_code, 403)
        self.assertIn("Invalid administrative credentials", body["detail"])

    # -------------------------------------------------------------------------
    # 6. Valid Credentials with Isolated Test Key (Must Succeed)
    # -------------------------------------------------------------------------

    def test_valid_x_admin_key_succeeds(self):
        valid_headers = {"X-Admin-Key": self.test_admin_key}
        payload = {
            "crop_id": "CR_OKRA",
            "market_id": "DEC_DAMBULLA",
            "market_name": "Dambulla DEC",
            "district_id": "LK-22",
            "price_date": "2026-10-15",
            "price_type": "wholesale",
            "price": 145.00,
            "data_source": "HARTI"
        }
        status_code, body, _ = self.dispatch_request(
            "POST",
            "/api/v1/market-prices",
            body=payload,
            headers=valid_headers
        )
        self.assertEqual(status_code, 201)
        self.assertIn("id", body)

    def test_valid_secondary_x_api_key_succeeds(self):
        valid_headers = {"X-API-Key": self.test_admin_key}
        payload = {
            "crop_id": "CR_PUMPKIN",
            "market_id": "DEC_DAMBULLA",
            "market_name": "Dambulla DEC",
            "district_id": "LK-22",
            "price_date": "2026-10-15",
            "price_type": "wholesale",
            "price": 85.00,
            "data_source": "HARTI"
        }
        status_code, body, _ = self.dispatch_request(
            "POST",
            "/api/v1/market-prices",
            body=payload,
            headers=valid_headers
        )
        self.assertEqual(status_code, 201)
        self.assertIn("id", body)

    def test_authorized_farmer_data_retrieval_succeeds(self):
        """Authorized requests can inspect budgets and analyses."""
        valid_headers = {"X-Admin-Key": self.test_admin_key}
        status_code, body, _ = self.dispatch_request(
            "GET",
            "/api/v1/cultivation-budgets",
            headers=valid_headers
        )
        self.assertEqual(status_code, 200)
        self.assertIn("items", body)

        status_code_a, body_a, _ = self.dispatch_request(
            "GET",
            "/api/v1/profit-analyses",
            headers=valid_headers
        )
        self.assertEqual(status_code_a, 200)
        self.assertIn("items", body_a)

    # -------------------------------------------------------------------------
    # 7. Public Historical & Planning Operations Preserved
    # -------------------------------------------------------------------------

    def test_public_get_market_prices_accessible(self):
        """Historical market prices remain publicly accessible for price trend exploration."""
        status_code, body, _ = self.dispatch_request("GET", "/api/v1/market-prices")
        self.assertEqual(status_code, 200)
        self.assertIn("items", body)
        self.assertIn("meta", body)

    def test_public_get_market_demands_accessible(self):
        """Market demand records remain publicly accessible for market demand analysis."""
        status_code, body, _ = self.dispatch_request("GET", "/api/v1/market-demands")
        self.assertEqual(status_code, 200)
        self.assertIn("items", body)
        self.assertIn("meta", body)

    def test_public_create_cultivation_budget_accessible(self):
        """Farmers can submit budgets without upfront administrative credentials."""
        payload = {
            "crop_id": "CR_TOMATO",
            "district_id": "LK-71",
            "season": "Maha",
            "year": 2026,
            "entry_mode": "quick",
            "total_cost": 220000.00,
            "expected_yield_kg": 6000.00
        }
        status_code, body, _ = self.dispatch_request("POST", "/api/v1/cultivation-budgets", body=payload)
        self.assertEqual(status_code, 201)
        self.assertIn("id", body)

    def test_public_create_profit_analysis_accessible(self):
        """Farmers can request harvest price and profit forecasts in real-time."""
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": "2026-12-25",
            "cultivation_extent_acres": 1.0,
            "estimated_production_kg": 5000.0,
            "budget_entry_mode": "quick",
            "quick_total_cost": 200000.0
        }
        status_code, body, _ = self.dispatch_request("POST", "/api/v1/profit-analyses", body=payload)
        self.assertEqual(status_code, 201)
        self.assertIn("analysis_reference", body)
        self.assertEqual(body["prediction_status"], "unavailable")

    # -------------------------------------------------------------------------
    # 8. OpenAPI Security Definitions
    # -------------------------------------------------------------------------

    def test_openapi_security_schemes_registered(self):
        schema = app.openapi()
        components = schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        self.assertIn(
            "AdminApiKeyHeader",
            security_schemes,
            "OpenAPI components/securitySchemes must document AdminApiKeyHeader"
        )
        self.assertEqual(security_schemes["AdminApiKeyHeader"]["name"], "X-Admin-Key")
        self.assertIn(
            "SecondaryApiKeyHeader",
            security_schemes,
            "OpenAPI components/securitySchemes must document SecondaryApiKeyHeader"
        )
        self.assertEqual(security_schemes["SecondaryApiKeyHeader"]["name"], "X-API-Key")


if __name__ == "__main__":
    unittest.main()
