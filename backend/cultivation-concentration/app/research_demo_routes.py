"""Research demo endpoints for historical scenario testing (2025 - August 2026).

These endpoints are strictly isolated from the live operational farmer database,
enforce historical date boundaries, and are disabled by default in production.
"""
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.schemas.research_demo import (
    HistoricalScenarioRequest,
    HistoricalScenarioResponse,
    ResearchDemoStatusResponse,
)
from app.services.research_metadata import (
    BENCHMARKS,
)
from app.services.research_disclosure import public_scenario

ISOLATED_DEMO_DB = str(Path(__file__).resolve().parents[1] / "storage/research_demo.sqlite3")


def is_research_demo_enabled() -> bool:
    env_val = os.getenv("CULTIVATION_RESEARCH_DEMO_ENABLED")
    if env_val is not None:
        return env_val.lower() == "true"
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False
    flag_file = Path(__file__).resolve().parents[1] / "storage/.research_demo_enabled"
    return flag_file.exists()


def router() -> APIRouter:
    routes = APIRouter(prefix="/api/research-demo", tags=["historical research demo"])

    @routes.get("/status", response_model=ResearchDemoStatusResponse)
    def status() -> Dict[str, Any]:
        enabled = is_research_demo_enabled()
        return {
            "enabled": enabled,
            "allowed_date_range": {
                "min_date": "2025-01-01",
                "max_date": "2026-08-31",
            },
            "supported_districts": ["Matara", "Hambantota"],
            "supported_crops": ["Bandakka", "Brinjal", "Pumpkin", "Corn", "Mung Beans", "Chillies"],
            "supported_models": ["XGBoost", "CatBoost", "Random Forest", "LinearSVC", "RBF SVC"],
            "benchmark_overview": BENCHMARKS,
            "isolated_database": Path(
                os.getenv("CULTIVATION_RESEARCH_DEMO_DB", ISOLATED_DEMO_DB)
            ).resolve().relative_to(Path(__file__).resolve().parents[1]).as_posix(),
        }

    @routes.post(
        "/evaluate",
        response_model=HistoricalScenarioResponse,
        responses={
            403: {"description": "Research demo workflow disabled"},
            422: {"description": "Historical date or input validation error"},
        },
    )
    def evaluate(payload: HistoricalScenarioRequest) -> Dict[str, Any]:
        if not is_research_demo_enabled():
            raise HTTPException(
                status_code=403,
                detail=(
                    "Research demo workflow is disabled. Set CULTIVATION_RESEARCH_DEMO_ENABLED=true "
                    "in the backend environment to enable historical scenario testing."
                ),
            )

        min_allowed = date(2025, 1, 1)
        max_allowed = date(2026, 8, 31)

        if payload.planting_date < min_allowed or payload.planting_date > max_allowed:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Historical research testing is permitted only for dates between "
                    f"{min_allowed.isoformat()} and {max_allowed.isoformat()}."
                ),
            )

        if payload.expected_harvest_date < payload.planting_date:
            raise HTTPException(
                status_code=422,
                detail="Expected harvest date must be on or after planting date.",
            )

        cutoff = payload.decision_cutoff or payload.planting_date
        if not min_allowed <= cutoff <= payload.planting_date:
            raise HTTPException(status_code=422, detail="Decision cutoff must be within the research date range and on or before planting.")
        if cutoff.year != payload.planting_date.year:
            raise HTTPException(status_code=422, detail="Decision cutoff and planting must be in the same calendar year; statistical-season mapping is unverified.")

        try:
            from app.services.historical_research_evaluator import evaluate_historical_scenario
            return evaluate_historical_scenario(
                district=payload.district,
                crop=payload.crop,
                season=payload.season,
                land_size_acres=payload.land_size_acres,
                planting_date=payload.planting_date,
                expected_harvest_date=payload.expected_harvest_date,
                model_name=payload.model_name,
                decision_cutoff=payload.decision_cutoff,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Historical research artifacts or evaluation unavailable; consult server configuration.",
            ) from exc

    return routes
