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


class TestProfitRiskAssessmentAPI(unittest.TestCase):
    """
    Automated integration tests for POST /api/v1/profit-analyses/assess-risk.
    Verifies HTTP responses, rule-based classification, transparent factors,
    preliminary heuristics disclaimer, statelessness, edge cases, input validation,
    and OpenAPI registration.
    """

    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        app.dependency_overrides[get_db] = lambda: self.session
        self.test_admin_key = "test-isolated-risk-api-key"
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

    def test_post_assess_risk_profitable_low_risk(self):
        """Verify profitable scenario: ROI >= 25% and Margin >= 20% classifies as Low Risk."""
        payload = {
            "expected_yield_kg": "2500.00",
            "selling_price_lkr_per_kg": "140.00",
            "total_cultivation_cost": "180000.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["risk_level"], "Low")
        self.assertEqual(data["assessment_type"], "rule_based_heuristic")
        self.assertFalse(data["is_ml_prediction"])
        self.assertIn("NOT a machine learning prediction", data["disclaimer"])
        self.assertIn("preliminary thresholds have NOT been scientifically validated", data["disclaimer"])

        # Applied thresholds
        self.assertEqual(data["thresholds_applied"]["min_roi_low_risk"], "25.0")
        self.assertEqual(data["thresholds_applied"]["min_margin_safety_low_risk"], "20.0")

        # Factors
        factors = data["factors"]
        self.assertEqual(factors["net_profit"], "170000.00")
        self.assertEqual(factors["roi_percentage"], "94.44")
        self.assertEqual(factors["breakeven_price_lkr_per_kg"], "72.00")
        self.assertEqual(factors["margin_of_safety_percentage"], "48.57")
        self.assertIn("ROI >= 25.0%", factors["trigger_rule"])
        self.assertIn("adequate cushion", factors["trigger_rationale"])

        # Embedded profit calculation
        profit_calc = data["profit_calculation"]
        self.assertEqual(profit_calc["gross_revenue"], "350000.00")
        self.assertEqual(profit_calc["net_profit"], "170000.00")
        self.assertEqual(profit_calc["breakeven_price_lkr_per_kg"], "72.00")
        self.assertEqual(profit_calc["roi_percentage"], "94.44")
        self.assertEqual(profit_calc["margin_of_safety_percentage"], "48.57")
        self.assertEqual(profit_calc["price_source"], "farmer_assumption")
        self.assertTrue(profit_calc["is_manual_price_assumption"])

    def test_post_assess_risk_exact_low_risk_boundary(self):
        """Exact boundary: ROI == 25.0% and Margin == 20.0% classifies as Low Risk."""
        payload = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "100.00",
            "total_cultivation_cost": "80000.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["risk_level"], "Low")
        self.assertEqual(data["factors"]["roi_percentage"], "25.00")
        self.assertEqual(data["factors"]["margin_of_safety_percentage"], "20.00")

    def test_post_assess_risk_just_below_boundary_medium_risk(self):
        """Just below boundary: ROI < 25% or Margin < 20% classifies as Medium Risk."""
        payload = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "99.90",
            "total_cultivation_cost": "80000.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["risk_level"], "Medium")
        self.assertIn("below the 25.0% Low Risk threshold", data["factors"]["trigger_rationale"])

    def test_post_assess_risk_breakeven_medium_risk(self):
        """Exact breakeven (net profit == 0, ROI == 0%): classified as Medium Risk."""
        payload = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "80.00",
            "total_cultivation_cost": "80000.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["risk_level"], "Medium")
        self.assertEqual(data["factors"]["net_profit"], "0.00")
        self.assertEqual(data["factors"]["roi_percentage"], "0.00")
        self.assertEqual(data["factors"]["margin_of_safety_percentage"], "0.00")

    def test_post_assess_risk_financial_loss_high_risk(self):
        """Financial loss (revenue < cost, net profit < 0, ROI < 0%): classified as High Risk."""
        payload = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "70.00",
            "total_cultivation_cost": "100000.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["risk_level"], "High")
        self.assertEqual(data["factors"]["net_profit"], "-30000.00")
        self.assertEqual(data["factors"]["roi_percentage"], "-30.00")
        self.assertIn("net_profit < 0", data["factors"]["trigger_rule"])
        self.assertIn("direct financial deficit", data["factors"]["trigger_rationale"])

    def test_post_assess_risk_zero_cultivation_cost(self):
        """Zero cultivation cost: returns explicit insufficient_information category, not invented risk."""
        payload = {
            "expected_yield_kg": "1200.00",
            "selling_price_lkr_per_kg": "95.00",
            "total_cultivation_cost": "0.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["risk_level"], "insufficient_information")
        self.assertIsNone(data["factors"]["roi_percentage"])
        self.assertIn("total_cultivation_cost == 0", data["factors"]["trigger_rule"])
        self.assertIn("ROI mathematically undefined", data["factors"]["trigger_rationale"])
        self.assertIsNone(data["profit_calculation"]["roi_percentage"])

    def test_post_assess_risk_default_omitted_cost(self):
        """When total_cultivation_cost is omitted, defaults to 0.0 -> insufficient_information."""
        payload = {
            "expected_yield_kg": "500.00",
            "selling_price_lkr_per_kg": "100.00"
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["risk_level"], "insufficient_information")
        self.assertEqual(data["factors"]["total_cultivation_cost"], "0.00")

    def test_post_assess_risk_custom_thresholds(self):
        """Custom thresholds override defaults and alter classification transparently."""
        payload = {
            "expected_yield_kg": "1000.00",
            "selling_price_lkr_per_kg": "130.00",
            "total_cultivation_cost": "100000.00",
            "thresholds": {
                "min_roi_low_risk": "50.0",
                "min_margin_safety_low_risk": "30.0"
            }
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )

        self.assertEqual(status_code, 200)
        # ROI = 30.0% < 50.0% threshold -> Medium Risk
        self.assertEqual(data["risk_level"], "Medium")
        self.assertEqual(data["thresholds_applied"]["min_roi_low_risk"], "50.0")
        self.assertEqual(data["thresholds_applied"]["min_margin_safety_low_risk"], "30.0")

    def test_post_assess_risk_statelessness(self):
        """Verify that risk assessment endpoint does NOT write to PostgreSQL."""
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
            "/api/v1/profit-analyses/assess-risk",
            body=payload
        )
        self.assertEqual(status_code, 200)

        final_count = self.session.execute(
            select(func.count(MarketProfitAnalysis.id))
        ).scalar_one()
        self.assertEqual(initial_count, final_count)

    def test_post_assess_risk_invalid_yield(self):
        """Yield <= 0 must return 422 Unprocessable Entity."""
        status_zero, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={"expected_yield_kg": "0.0", "selling_price_lkr_per_kg": "100.0"}
        )
        self.assertEqual(status_zero, 422)

        status_neg, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={"expected_yield_kg": "-500.0", "selling_price_lkr_per_kg": "100.0"}
        )
        self.assertEqual(status_neg, 422)

    def test_post_assess_risk_invalid_price(self):
        """Price <= 0 must return 422 Unprocessable Entity."""
        status_zero, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={"expected_yield_kg": "1000.0", "selling_price_lkr_per_kg": "0.0"}
        )
        self.assertEqual(status_zero, 422)

        status_neg, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={"expected_yield_kg": "1000.0", "selling_price_lkr_per_kg": "-25.0"}
        )
        self.assertEqual(status_neg, 422)

    def test_post_assess_risk_negative_cost(self):
        """Cost < 0 must return 422 Unprocessable Entity."""
        status_neg, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={
                "expected_yield_kg": "1000.0",
                "selling_price_lkr_per_kg": "100.0",
                "total_cultivation_cost": "-5000.0"
            }
        )
        self.assertEqual(status_neg, 422)

    def test_post_assess_risk_nan_inf_rejected(self):
        """NaN and Infinity values must return 422 Unprocessable Entity."""
        status_nan, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={
                "expected_yield_kg": "NaN",
                "selling_price_lkr_per_kg": "100.0",
                "total_cultivation_cost": "5000.0"
            }
        )
        self.assertEqual(status_nan, 422)

        status_inf, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={
                "expected_yield_kg": "1000.0",
                "selling_price_lkr_per_kg": "Infinity",
                "total_cultivation_cost": "5000.0"
            }
        )
        self.assertEqual(status_inf, 422)

    def test_post_assess_risk_missing_required_fields(self):
        """Missing required fields must return 422."""
        status_missing, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={"total_cultivation_cost": "5000.0"}
        )
        self.assertEqual(status_missing, 422)

    def test_post_assess_risk_invalid_thresholds(self):
        """Invalid threshold parameters must return 422."""
        status_neg_roi, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={
                "expected_yield_kg": "1000.0",
                "selling_price_lkr_per_kg": "100.0",
                "thresholds": {"min_roi_low_risk": "-5.0"}
            }
        )
        self.assertEqual(status_neg_roi, 422)

        status_bad_margin, _ = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={
                "expected_yield_kg": "1000.0",
                "selling_price_lkr_per_kg": "100.0",
                "thresholds": {"min_margin_safety_low_risk": "120.0"}
            }
        )
        self.assertEqual(status_bad_margin, 422)

    def test_route_ordering_not_intercepted_by_analysis_id(self):
        """
        Verify that POST /assess-risk is handled by assess_profit_risk_endpoint
        and that /{analysis_id} does not intercept it.
        """
        status_post, data = self.client_request(
            "POST",
            "/api/v1/profit-analyses/assess-risk",
            body={"expected_yield_kg": "1000.0", "selling_price_lkr_per_kg": "100.0"}
        )
        self.assertEqual(status_post, 200)

        # GET /assess-risk routes to get_analysis_endpoint where "assess-risk" is treated as an analysis_id
        # and returns 404 because no analysis with that ID exists.
        status_get, _ = self.client_request(
            "GET",
            "/api/v1/profit-analyses/assess-risk",
            as_admin=True
        )
        self.assertEqual(status_get, 404)

    def test_openapi_documentation_registered(self):
        """Verify endpoint is documented in FastAPI OpenAPI schema."""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})
        self.assertIn("/api/v1/profit-analyses/assess-risk", paths)
        post_op = paths["/api/v1/profit-analyses/assess-risk"].get("post")
        self.assertIsNotNone(post_op)
        self.assertEqual(post_op.get("summary"), "Stateless rule-based profit risk assessment")
        self.assertIn("200", post_op.get("responses", {}))


if __name__ == "__main__":
    unittest.main()
