from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import unittest
from urllib.parse import urlencode
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models.market_demand import MarketDemand
from app.schemas.common import DemandLevel, PredictionStatus
from app.schemas.demand_forecast import DemandForecastRequest, DemandForecastResponse
from app.services.demand_prediction_service import (
    AbstractDemandPredictor,
    get_demand_predictor,
)


class MockTrainedDemandPredictor:
    """Mock predictor simulating a trained ML model for dependency injection testing."""

    def predict_demand(self, request: DemandForecastRequest) -> DemandForecastResponse:
        return DemandForecastResponse(
            crop_id=request.crop_id,
            cultivation_district_id=request.cultivation_district_id,
            target_market_id=request.target_market_id,
            target_market_name="Dambulla Dedicated Economic Centre",
            forecast_target_date=request.forecast_target_date,
            prediction_status=PredictionStatus.COMPLETED,
            projected_demand_volume_kg=Decimal("450000.00"),
            projected_demand_level=DemandLevel.HIGH,
            model_version="xgb-demand-v1.0.0",
            model_provenance={
                "algorithm": "XGBoostRegressor",
                "training_period": "2018-2025",
                "mae_metric": 1250.50
            },
            status_message="Demand prediction generated successfully by trained model.",
            created_at=datetime.now()
        )


class TestMarketDemandForecastAPI(unittest.TestCase):
    """
    Automated integration tests for POST /api/v1/market-demands/forecast.
    Verifies request validation, past date rejection, default unavailable response,
    dependency-injected predictor swappability, route ordering, and statelessness.
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

    def test_forecast_default_unavailable_model(self):
        """Verify default predictor returns structured 200 unavailable response with null outputs."""
        target_date = str(date.today() + timedelta(days=45))
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": target_date
        }

        status_code, data = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["crop_id"], "CR_TOMATO")
        self.assertEqual(data["cultivation_district_id"], "LK-71")
        self.assertEqual(data["target_market_id"], "DEC_DAMBULLA")
        self.assertEqual(data["target_market_name"], "Dambulla Dedicated Economic Centre")
        self.assertEqual(data["forecast_target_date"], target_date)
        self.assertEqual(data["prediction_status"], "unavailable")
        self.assertIsNone(data["projected_demand_volume_kg"])
        self.assertIsNone(data["projected_demand_level"])
        self.assertIsNone(data["model_version"])
        self.assertIsNone(data["model_provenance"])
        self.assertIn("currently offline or undergoing training", data["status_message"])

    def test_forecast_statelessness_no_database_write(self):
        """Verify that calling /forecast does not write to market_demand_records table in PostgreSQL."""
        initial_count = self.session.execute(
            select(func.count(MarketDemand.id))
        ).scalar_one()

        target_date = str(date.today() + timedelta(days=30))
        payload = {
            "crop_id": "CR_CHILLI",
            "cultivation_district_id": "LK-82",
            "target_market_id": "DEC_PETTAH",
            "forecast_target_date": target_date
        }
        status_code, _ = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )
        self.assertEqual(status_code, 200)

        final_count = self.session.execute(
            select(func.count(MarketDemand.id))
        ).scalar_one()
        self.assertEqual(initial_count, final_count)

    def test_forecast_dependency_injection_override(self):
        """Verify that dependency injection allows plugging in a trained model predictor."""
        # Inject mock trained predictor
        app.dependency_overrides[get_demand_predictor] = lambda: MockTrainedDemandPredictor()

        target_date = str(date.today() + timedelta(days=60))
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": target_date
        }

        status_code, data = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(data["prediction_status"], "completed")
        self.assertEqual(data["projected_demand_volume_kg"], "450000.00")
        self.assertEqual(data["projected_demand_level"], "High")
        self.assertEqual(data["model_version"], "xgb-demand-v1.0.0")
        self.assertEqual(data["model_provenance"]["algorithm"], "XGBoostRegressor")

    def test_forecast_past_date_rejected(self):
        """Past date must be rejected with HTTP 422."""
        past_date = str(date.today() - timedelta(days=5))
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": past_date
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )
        self.assertEqual(status_code, 422)
        self.assertIn("cannot be in the past", json.dumps(data))

    def test_forecast_today_date_accepted(self):
        """Current date (today) is valid for immediate forecast."""
        today_date = str(date.today())
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": today_date
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(data["forecast_target_date"], today_date)

    def test_forecast_invalid_crop_id_rejected(self):
        """Invalid crop ID not in catalog is rejected with 422."""
        payload = {
            "crop_id": "CR_INVALID_CROP_XYZ",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": str(date.today() + timedelta(days=10))
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )
        self.assertEqual(status_code, 422)
        self.assertIn("Invalid crop_id", json.dumps(data))

    def test_forecast_invalid_district_id_rejected(self):
        """Invalid district code is rejected with 422."""
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-99",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": str(date.today() + timedelta(days=10))
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )
        self.assertEqual(status_code, 422)
        self.assertIn("Invalid district_id", json.dumps(data))

    def test_forecast_invalid_market_id_rejected(self):
        """Unverified market ID not in standard DEC catalog is rejected with 422."""
        payload = {
            "crop_id": "CR_TOMATO",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_UNKNOWN_HUB",
            "forecast_target_date": str(date.today() + timedelta(days=10))
        }
        status_code, data = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )
        self.assertEqual(status_code, 422)
        self.assertIn("Invalid target_market_id", json.dumps(data))

    def test_forecast_missing_fields_rejected(self):
        """Missing required parameters return 422."""
        status_code, _ = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body={"crop_id": "CR_TOMATO"}
        )
        self.assertEqual(status_code, 422)

    def test_route_ordering_no_conflict_with_id_route(self):
        """
        Verify that POST /forecast correctly dispatches to forecast_demand_endpoint,
        and that a GET /forecast routes to /{demand_id} and fails with 422 (since 'forecast' is not int).
        """
        payload = {
            "crop_id": "CR_MAIZE",
            "cultivation_district_id": "LK-71",
            "target_market_id": "DEC_DAMBULLA",
            "forecast_target_date": str(date.today() + timedelta(days=20))
        }
        status_post, _ = self.client_request(
            "POST",
            "/api/v1/market-demands/forecast",
            body=payload
        )
        self.assertEqual(status_post, 200)

        # GET /forecast routes to /{demand_id} expecting an int
        status_get, _ = self.client_request(
            "GET",
            "/api/v1/market-demands/forecast"
        )
        self.assertEqual(status_get, 422)

    def test_openapi_documentation_registered(self):
        """Verify endpoint is documented in FastAPI OpenAPI schema."""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})
        self.assertIn("/api/v1/market-demands/forecast", paths)
        post_op = paths["/api/v1/market-demands/forecast"].get("post")
        self.assertIsNotNone(post_op)
        self.assertEqual(post_op.get("summary"), "Stateless ML-ready commodity demand forecasting")
        self.assertIn("200", post_op.get("responses", {}))


if __name__ == "__main__":
    unittest.main()
