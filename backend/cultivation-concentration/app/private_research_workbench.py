"""Explicitly authorized private localhost testing; never mounted on the farmer API.

Run with python -m app.private_research_workbench. Only the loopback listener
serves model classes to a separate researcher credential. No farmer records,
publication permission, operational risk or agronomic approvals are created.
"""
import argparse
import hashlib
import ipaddress
import os
from pathlib import Path
import secrets
from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from app.schemas.research_demo import HistoricalScenarioRequest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "4397ddae6a3fabde06f1b9dc6fd42d40b3f0cc5a5275754621011e4cfcbb2bab"
MIN_DATE, MAX_DATE = date(2025, 1, 1), date(2026, 8, 31)


class PrivatePrediction(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    mode: Literal["private_local_model_test"] = "private_local_model_test"
    status: Literal["historical_proxy_prediction", "insufficient_research_coverage"]
    scenario: HistoricalScenarioRequest
    model_name: str
    model_crop_category: str
    trained_through: int
    training_cutoff_basis: str
    classification: Literal["Low", "Medium", "High"] | None
    class_probabilities: dict[str, float] | None
    feature_names: list[str]
    observation_availability: str
    interpretation: str
    operational_status: Literal["risk_level_not_yet_validated"] = "risk_level_not_yet_validated"
    recommendation_status: Literal["blocked_unvalidated_risk"] = "blocked_unvalidated_risk"


def create_workbench(token: str, evaluator=None) -> FastAPI:
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("A separate strong researcher credential is required")
    app = FastAPI(title="Private local historical model workbench", docs_url=None, redoc_url=None, openapi_url=None)
    security = HTTPBearer(auto_error=False)

    @app.middleware("http")
    async def private_boundary(request: Request, call_next):
        try:
            local = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
        except ValueError:
            local = False
        # No forwarded-header trust, DNS rebinding, credentialed CORS or cross-origin reads.
        valid_host = request.url.hostname in ("127.0.0.1", "localhost", "::1")
        origin = request.headers.get("origin")
        same_origin = origin is None or origin == f"{request.url.scheme}://{request.headers.get('host')}"
        if not local or not valid_host or not same_origin:
            response = JSONResponse({"detail": "Private workbench accepts same-origin loopback requests only"}, status_code=403)
        else:
            response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    def researcher(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
        if credentials is None or not secrets.compare_digest(credentials.credentials, token):
            raise HTTPException(401, "Unlock using the separate local researcher credential")

    @app.get("/", response_class=HTMLResponse)
    def page():
        return (ROOT / "app/workbench/index.html").read_text(encoding="utf-8")

    @app.get("/workbench.css")
    def stylesheet():
        from fastapi.responses import Response
        return Response((ROOT / "app/workbench/workbench.css").read_text(encoding="utf-8"), media_type="text/css")

    @app.get("/workbench.js")
    def javascript():
        from fastapi.responses import Response
        return Response((ROOT / "app/workbench/workbench.js").read_text(encoding="utf-8"), media_type="text/javascript")

    @app.get("/api/private-research/status", dependencies=[Depends(researcher)])
    def status():
        return dict(mode="private_local_model_test", min_date=MIN_DATE, max_date=MAX_DATE,
            source="private historical CSV, not live farmer registrations", saved_training_through=2024,
            operational_status="risk_level_not_yet_validated")

    @app.post("/api/private-research/evaluate", response_model=PrivatePrediction, dependencies=[Depends(researcher)])
    def evaluate(value: HistoricalScenarioRequest):
        cutoff = value.decision_cutoff or value.planting_date
        if not MIN_DATE <= value.planting_date <= MAX_DATE:
            raise HTTPException(422, "Historical model tests require planting between 2025-01-01 and 2026-08-31; later dates are outside this research scope")
        if not MIN_DATE <= cutoff <= value.planting_date or cutoff.year != value.planting_date.year:
            raise HTTPException(422, "Decision cutoff must precede or equal planting in the same calendar year and supported research range")
        if value.expected_harvest_date < value.planting_date:
            raise HTTPException(422, "Expected harvest cannot precede planting")
        try:
            if evaluator is None:
                source = ROOT / "data/legacy/official_farmer_cultivation_2020_2026.csv"
                if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
                    raise ValueError("Historical source version changed")
                from app.services.historical_research_evaluator import evaluate_historical_scenario
                result = evaluate_historical_scenario(**value.model_dump(), allow_sparse=True)
            else:
                result = evaluator(**value.model_dump())
        except Exception as exc:
            # No private dataset/path/record information in failures.
            raise HTTPException(503, "Private model inputs/artifacts unavailable or incompatible; check the authorized local bundle") from exc
        metadata = result["model_metadata"]
        return PrivatePrediction(status=result["status"], scenario=value, model_name=metadata["model_name"],
            model_crop_category=metadata.get("model_crop_category", value.crop),
            trained_through=metadata["trained_through"], training_cutoff_basis=metadata["training_cutoff_basis"],
            classification=result["prediction"]["historical_proxy_label"],
            class_probabilities=result["prediction"]["class_probabilities"], feature_names=metadata["feature_names"],
            observation_availability=result["observation_availability"]["status"],
            interpretation="Frozen historical model classification, not validated current risk. Unknown observation availability remains a replay assumption; no zero-leakage or untouched-holdout claim follows. No live registrations or farmer recommendations are changed.")

    return app


def local_credential(path: Path) -> str:
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if len(token) < 32:
            raise ValueError("Existing researcher credential is invalid; refusing to overwrite it")
        return token
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(token + "\n")
    return token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Invalid local port")
    credential_path = ROOT / "storage/private_research_workbench_token.txt"
    app = create_workbench(local_credential(credential_path))
    print(f"Private model testing: http://127.0.0.1:{args.port}")
    print(f"Choose this local credential file to unlock: {credential_path}")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, proxy_headers=False, access_log=False)


if __name__ == "__main__":
    main()
