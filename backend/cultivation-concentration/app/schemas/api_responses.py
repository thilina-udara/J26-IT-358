"""Stable outer response contracts; variable evidence payloads remain intact."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict
from app.schemas.cultivation_plan import Plan, Crop, Season


class CompatibleResponse(BaseModel):
    # Preserve extra evidence/privacy annotations already returned by services.
    model_config = ConfigDict(extra='allow')


class HealthResponse(BaseModel):
    status: Literal['healthy']


class DependencyCheck(BaseModel):
    status: str
    required: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal['ready', 'not_ready']
    checks: dict[str, DependencyCheck]
    research_validation: Literal['not_asserted']


class ErrorResponse(BaseModel):
    # Existing HTTPException strings and FastAPI validation error lists are preserved.
    detail: str | list[dict[str, Any]]


def error_responses(*codes):
    descriptions = {
        401: 'Missing, invalid, expired or revoked farmer credentials',
        403: 'Identity mismatch or insufficient role/eligibility permissions',
        404: 'Owned resource not found or not available at the analysis cutoff',
        409: 'Duplicate, cancelled, changed plan or ineligible selection',
        422: 'Invalid input, filter, pagination or analysis cutoff',
        429: 'Authentication attempt limit reached; Retry-After is provided',
        503: 'Essential dependency or evidence configuration unavailable',
    }
    return {code: {'model': ErrorResponse, 'description': descriptions[code]} for code in codes}


class RiskAssessmentResponse(CompatibleResponse):
    status: str
    risk_level: str | None
    indicators: dict[str, Any]
    explanations: dict[str, str]
    missing_evidence: list[str]
    interpretation: str


class AlternativeComparisonResponse(CompatibleResponse):
    status: str
    as_of: str
    selected_crop: Crop
    selected_concentration: dict[str, Any]
    alternatives: list[dict[str, Any]]
    comparisons: list[dict[str, Any]]
    risk_level: str
    interpretation: str


class PersonalizedPlanResponse(CompatibleResponse):
    status: str
    plan_id: str
    final_crop: Crop
    as_of: str
    request: dict[str, Any]
    expected_harvest_date: str
    activities: list[dict[str, Any]]
    warnings: list[str]
    missing_categories: list[str]
    based_on_updated_at: str


class PersonalizedRevision(CompatibleResponse):
    revision_id: int
    saved_at: str


class SavedPersonalizedPlanResponse(CompatibleResponse):
    personalized_plan: PersonalizedPlanResponse
    revision_id: int
    revisions: list[PersonalizedRevision]
    stale: bool


class SeasonContext(BaseModel):
    farmer_declared_season: Season | None
    requested_season: Season | None
    effective_analysis_season: Season | None
    source: Literal['analysis_request', 'farmer_declaration', 'unknown']
    conflict: bool
    independently_verified_statistical_season: None = None
    interpretation: str


class WorkflowReportResponse(CompatibleResponse):
    season_context: SeasonContext | None = None
    status: str
    analysis_status: str
    missing_evidence: list[str]
    workflow_version: str
    plan_id: str
    as_of: str
    historical_prediction: dict[str, Any]
    current_plan_risk: dict[str, Any]
    experimental_production_assessment: dict[str, Any]
    experimental_alternatives: list[dict[str, Any]]
    experimental_reference_assessment: dict[str, Any]
    assessment: dict[str, Any]
    clustering: dict[str, Any]
    recommendations: dict[str, Any]
    next_step: str
    planning_status: str


class WorkflowSubmitResponse(BaseModel):
    plan: Plan
    workflow: WorkflowReportResponse


class WorkflowReadResponse(BaseModel):
    plan: Plan
    personalized_plan: SavedPersonalizedPlanResponse | None
