import uuid
from datetime import date
from math import ceil
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.models.profit_analysis import MarketProfitAnalysis
from app.models.cultivation_cost import CultivationBudget
from app.schemas.profit_analysis import FarmerAnalysisInput, PaginatedProfitAnalysisResponse, PredictionResultResponse
from app.schemas.common import PaginationMeta, PredictionStatus


def create_profit_analysis(db: Session, data: FarmerAnalysisInput) -> MarketProfitAnalysis:
    """
    Register a farmer profit analysis request and create a persistent analysis record.
    If cultivation_budget_id is provided, validates that the budget exists.
    Maintains ML independence: marks prediction_status as 'unavailable' until ML inference pipeline is connected,
    leaving all forecasted outputs strictly null without fabricating predictions.
    """
    estimated_cost = data.resolve_total_cost()

    if data.cultivation_budget_id:
        budget = db.execute(
            select(CultivationBudget).where(CultivationBudget.id == data.cultivation_budget_id)
        ).scalar_one_or_none()
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced cultivation budget ID {data.cultivation_budget_id} does not exist."
            )
        if estimated_cost <= 0:
            estimated_cost = budget.total_cost

    analysis_ref = f"REF-{uuid.uuid4().hex[:10].upper()}"

    analysis_record = MarketProfitAnalysis(
        analysis_reference=analysis_ref,
        crop_id=data.crop_id,
        cultivation_district_id=data.cultivation_district_id,
        target_market_id=data.target_market_id,
        target_market_name=data.target_market_name,
        cultivation_budget_id=data.cultivation_budget_id,
        prediction_status=PredictionStatus.UNAVAILABLE.value,
        forecast_target_date=data.forecast_target_date,
        forecast_horizon_days=data.forecast_horizon_days,
        cultivation_extent_acres=data.cultivation_extent_acres,
        estimated_production_kg=data.estimated_production_kg,
        estimated_total_cost=estimated_cost,
        error_message="ML inference models are currently offline or undergoing scheduled retraining."
    )
    db.add(analysis_record)
    db.commit()
    db.refresh(analysis_record)
    return analysis_record


def get_profit_analysis(db: Session, identifier: str) -> Optional[MarketProfitAnalysis]:
    """Retrieve a profit analysis by its database ID or unique reference string."""
    if identifier.isdigit():
        record = db.execute(
            select(MarketProfitAnalysis).where(MarketProfitAnalysis.id == int(identifier))
        ).scalar_one_or_none()
        if record:
            return record

    return db.execute(
        select(MarketProfitAnalysis).where(MarketProfitAnalysis.analysis_reference == identifier)
    ).scalar_one_or_none()


def list_profit_analyses(
    db: Session,
    crop_id: Optional[str] = None,
    cultivation_district_id: Optional[str] = None,
    target_market_id: Optional[str] = None,
    prediction_status: Optional[str] = None,
    profit_risk_level: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 50
) -> PaginatedProfitAnalysisResponse:
    """Query saved profit analyses with filtering and pagination."""
    query = select(MarketProfitAnalysis)
    count_query = select(func.count(MarketProfitAnalysis.id))

    filters = []
    if crop_id:
        filters.append(MarketProfitAnalysis.crop_id == crop_id)
    if cultivation_district_id:
        filters.append(MarketProfitAnalysis.cultivation_district_id == cultivation_district_id)
    if target_market_id:
        filters.append(MarketProfitAnalysis.target_market_id == target_market_id)
    if prediction_status:
        filters.append(MarketProfitAnalysis.prediction_status == prediction_status)
    if profit_risk_level:
        filters.append(MarketProfitAnalysis.profit_risk_level == profit_risk_level)
    if start_date:
        filters.append(MarketProfitAnalysis.forecast_target_date >= start_date)
    if end_date:
        filters.append(MarketProfitAnalysis.forecast_target_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total = db.execute(count_query).scalar_one()

    page = max(1, page)
    page_size = min(100, max(1, page_size))
    total_pages = ceil(total / page_size) if total > 0 else 1

    items = db.execute(
        query.order_by(MarketProfitAnalysis.forecast_target_date.desc(), MarketProfitAnalysis.id.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
    ).scalars().all()

    return PaginatedProfitAnalysisResponse(
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        ),
        items=[format_profit_analysis_response(it) for it in items]
    )


def delete_profit_analysis(db: Session, identifier: str) -> bool:
    """Delete a profit analysis by ID or reference string."""
    record = get_profit_analysis(db, identifier)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def format_profit_analysis_response(record: MarketProfitAnalysis) -> PredictionResultResponse:
    """Helper to convert ORM model to standardized prediction response with appropriate status message."""
    resp = PredictionResultResponse.model_validate(record)
    if record.prediction_status == PredictionStatus.UNAVAILABLE.value:
        resp.status_message = "Machine learning models are currently unavailable."
    elif record.prediction_status == PredictionStatus.COMPLETED.value:
        resp.status_message = "Prediction completed successfully."
    elif record.prediction_status == PredictionStatus.FAILED.value:
        resp.status_message = "Prediction execution failed during processing."
    elif record.prediction_status == PredictionStatus.PENDING.value:
        resp.status_message = "Analysis request received and queued."
    return resp
