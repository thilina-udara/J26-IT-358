import json
import unittest
from decimal import Decimal
from urllib.parse import urlencode
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models.profit_analysis import MarketProfitAnalysis


class TestProfitCalculationAPI(unittest.TestCase):
    """
    Automated integration tests for POST /api/v1/profit-analyses/calculate.
    Verifies HTTP responses, financial calculations, statelessness, edge cases,
    input validation, and route resolution.
    """

    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        app.dependency_overrides[get_db] = lambda: self.session
        self.test_admin_key = "test-isolated-crud-key-temp"
        self.original_admin_key = settings.ADMIN_API_KEY
        settings.ADMIN_API_KEY = self.test_admin_key

    def tearDown(self):
        settings.ADMIN_API_KEY = self.original_admin_key
        app.dependency_overrides.clear()
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    def client_request(
        self,
        method: str,
        path: str,
        body: dict = None,
        params: dict = None,
        headers: dict = None,
        as_admin: bool = False
    ):
        """Dispatch ASGI request directly through FastAPI application."""
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        query_string = urlencode(params).encode("ascii") if params else b""
        req_headers = [(b"host", b"localhost")]
        if body is not None:
            req_headers.append((b"content-type", b"application/json"))
        if as_admin:
            req_headers.append((b"x-admin-key", self.test_admin_key.encode("utf-8")))
        if headers:
            for k, v in headers.items():
                req_headers.append((k.lower().encode("utf-8"), v.encode("utf-8")))

        status_code = None
        body_parts = []

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query_string,
            "headers": req_headers,
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 80),
        }

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        async def send(message):
            nonlocal status_code, body_parts
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        import asyncio
        asyncio.run(app(scope, receive, send))
        response_body = b"".join(body_parts).decode("utf-8")
        parsed_json = json.loads(response_body) if response_body else None
        return status_code, parsed_json

    def test_post_calculate_profitable_scenario(self):
        """Verify profitable scenario: yields 200 OK with correct math and provenance."""
        payload = {
            "expected_yield_kg": "2500.00",
            "selling_price_lkr_per_kg": "140.00",
            "total_cultivation_cost": "180000.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body=payload
        )

        self.assertEqual(status_code, 200)
        # Expected Yield = 2500, Price = 140 -> Revenue = 350,000.00
        self.assertEqual(data["gross_revenue"], "350000.00")
        # Net Profit = 350,000 - 180,000 = 170,000.00
        self.assertEqual(data["net_profit"], "170000.00")
        # Breakeven Price = 180,000 / 2500 = 72.00
        self.assertEqual(data["breakeven_price_lkr_per_kg"], "72.00")
        # ROI = (170,000 / 180,000) * 100 = 94.44%
        self.assertEqual(data["roi_percentage"], "94.44")
        # Margin of Safety = ((140 - 72) / 140) * 100 = 48.57%
        self.assertEqual(data["margin_of_safety_percentage"], "48.57")
        # Farmer assumption provenance
        self.assertEqual(data["price_source"], "farmer_assumption")
        self.assertTrue(data["is_manual_price_assumption"])
        self.assertIn("planning assumption", data["assumptions_note"])
        self.assertIsNone(data["calculation_notes"])

    def test_post_calculate_financial_loss_scenario(self):
        """Verify financial loss scenario: negative net profit and negative ROI."""
        payload = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "70.00",
            "total_cultivation_cost": "100000.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["gross_revenue"], "70000.00")
        self.assertEqual(data["net_profit"], "-30000.00")
        self.assertEqual(data["breakeven_price_lkr_per_kg"], "100.00")
        self.assertEqual(data["roi_percentage"], "-30.00")
        self.assertEqual(data["margin_of_safety_percentage"], "-42.86")

    def test_post_calculate_zero_cultivation_cost(self):
        """Verify zero cost: ROI is null and explanation notes are populated."""
        payload = {
            "expected_yield_kg": "1200.00",
            "selling_price_lkr_per_kg": "95.00",
            "total_cultivation_cost": "0.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["gross_revenue"], "114000.00")
        self.assertEqual(data["net_profit"], "114000.00")
        self.assertEqual(data["breakeven_price_lkr_per_kg"], "0.00")
        self.assertIsNone(data["roi_percentage"])
        self.assertEqual(data["margin_of_safety_percentage"], "100.00")
        self.assertIn("ROI is mathematically undefined", data["calculation_notes"])

    def test_post_calculate_default_omitted_cost(self):
        """Verify that total_cultivation_cost defaults to 0.0 when omitted."""
        payload = {
            "expected_yield_kg": "500.00",
            "selling_price_lkr_per_kg": "100.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["gross_revenue"], "50000.00")
        self.assertEqual(data["net_profit"], "50000.00")
        self.assertIsNone(data["roi_percentage"])

    def test_post_calculate_statelessness(self):
        """Verify that calculate endpoint does NOT insert any rows into PostgreSQL."""
        initial_count = self.session.execute(
            select(func.count(MarketProfitAnalysis.id))
        ).scalar_one()

        payload = {
            "expected_yield_kg": "3000.00",
            "selling_price_lkr_per_kg": "150.00",
            "total_cultivation_cost": "200000.00"
        }
        status_code, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body=payload
        )
        self.assertEqual(status_code, 200)

        final_count = self.session.execute(
            select(func.count(MarketProfitAnalysis.id))
        ).scalar_one()
        self.assertEqual(initial_count, final_count)

    def test_post_calculate_invalid_yield(self):
        """Yield <= 0 must return 422 Unprocessable Entity."""
        status_zero, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={"expected_yield_kg": "0.0", "selling_price_lkr_per_kg": "100.0"}
        )
        self.assertEqual(status_zero, 422)

        status_neg, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={"expected_yield_kg": "-500.0", "selling_price_lkr_per_kg": "100.0"}
        )
        self.assertEqual(status_neg, 422)

    def test_post_calculate_invalid_price(self):
        """Price <= 0 must return 422 Unprocessable Entity."""
        status_zero, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={"expected_yield_kg": "1000.0", "selling_price_lkr_per_kg": "0.0"}
        )
        self.assertEqual(status_zero, 422)

        status_neg, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={"expected_yield_kg": "1000.0", "selling_price_lkr_per_kg": "-15.0"}
        )
        self.assertEqual(status_neg, 422)

    def test_post_calculate_negative_cost(self):
        """Cost < 0 must return 422 Unprocessable Entity."""
        status_neg, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={
                "expected_yield_kg": "1000.0",
                "selling_price_lkr_per_kg": "100.0",
                "total_cultivation_cost": "-5000.0"
            }
        )
        self.assertEqual(status_neg, 422)

    def test_post_calculate_nan_inf_rejected(self):
        """NaN and Infinity values must return 422 Unprocessable Entity."""
        status_nan, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={
                "expected_yield_kg": "NaN",
                "selling_price_lkr_per_kg": "100.0",
                "total_cultivation_cost": "5000.0"
            }
        )
        self.assertEqual(status_nan, 422)

        status_inf, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={
                "expected_yield_kg": "1000.0",
                "selling_price_lkr_per_kg": "Infinity",
                "total_cultivation_cost": "5000.0"
            }
        )
        self.assertEqual(status_inf, 422)

    def test_post_calculate_missing_required_fields(self):
        """Missing required fields must return 422."""
        status_missing, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={"total_cultivation_cost": "5000.0"}
        )
        self.assertEqual(status_missing, 422)

    def test_route_ordering_not_intercepted_by_analysis_id(self):
        """
        Verify that POST /calculate is handled by calculate_profit_endpoint
        and that /{analysis_id} does not intercept it.
        """
        # POST /calculate works cleanly
        status_post, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/calculate",
            body={"expected_yield_kg": "1000.0", "selling_price_lkr_per_kg": "100.0"}
        )
        self.assertEqual(status_post, 200)

        # GET /calculate routes to get_analysis_endpoint where "calculate" is treated as an analysis_id
        # and returns 404 because no analysis with ID "calculate" exists.
        status_get, _ = self.client_request(
            "GET",
            "/api/v1/profit-analyses/calculate",
            as_admin=True
        )
        self.assertEqual(status_get, 404)

    def test_openapi_documentation_registered(self):
        """Verify endpoint is documented in FastAPI OpenAPI schema."""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})
        self.assertIn("/api/v1/profit-analyses/calculate", paths)
        post_op = paths["/api/v1/profit-analyses/calculate"].get("post")
        self.assertIsNotNone(post_op)
        self.assertEqual(post_op.get("summary"), "Stateless deterministic profit calculation")
        self.assertIn("200", post_op.get("responses", {}))


if __name__ == "__main__":
    unittest.main()
