from datetime import date
from math import ceil
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.models.market_demand import MarketDemand
from app.schemas.market_demand import MarketDemandCreate, PaginatedMarketDemandResponse, MarketDemandResponse
from app.schemas.common import DemandRecordType, PaginationMeta


def create_market_demand(db: Session, data: MarketDemandCreate) -> MarketDemand:
    """
    Create a new commodity market demand record.
    Enforces that synthetic records are never marked as training eligible.
    """
    # Enforce data contamination defense
    training_eligible = data.is_training_eligible
    if data.record_type == DemandRecordType.SYNTHETIC:
        training_eligible = False

    demand_record = MarketDemand(
        crop_id=data.crop_id,
        district_id=data.district_id,
        market_id=data.market_id,
        period_start_date=data.period_start_date,
        period_end_date=data.period_end_date,
        demand_volume_kg=data.demand_volume_kg,
        unit=data.unit,
        record_type=data.record_type.value,
        demand_level=data.demand_level.value if data.demand_level else None,
        confidence_score=data.confidence_score,
        estimation_method=data.estimation_method,
        is_training_eligible=training_eligible,
        data_source=data.data_source,
        notes=data.notes
    )
    db.add(demand_record)
    db.commit()
    db.refresh(demand_record)
    return demand_record


def get_market_demand(db: Session, demand_id: int) -> Optional[MarketDemand]:
    """Retrieve an individual market demand entry by ID."""
    return db.execute(
        select(MarketDemand).where(MarketDemand.id == demand_id)
    ).scalar_one_or_none()


def list_market_demands(
    db: Session,
    crop_id: Optional[str] = None,
    district_id: Optional[str] = None,
    market_id: Optional[str] = None,
    record_type: Optional[str] = None,
    demand_level: Optional[str] = None,
    is_training_eligible: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 50
) -> PaginatedMarketDemandResponse:
    """Query market demand records with multi-criteria filtering and pagination."""
    query = select(MarketDemand)
    count_query = select(func.count(MarketDemand.id))

    filters = []
    if crop_id:
        filters.append(MarketDemand.crop_id == crop_id)
    if district_id:
        filters.append(MarketDemand.district_id == district_id)
    if market_id:
        filters.append(MarketDemand.market_id == market_id)
    if record_type:
        filters.append(MarketDemand.record_type == record_type)
    if demand_level:
        filters.append(MarketDemand.demand_level == demand_level)
    if is_training_eligible is not None:
        filters.append(MarketDemand.is_training_eligible == is_training_eligible)
    if start_date:
        filters.append(MarketDemand.period_start_date >= start_date)
    if end_date:
        filters.append(MarketDemand.period_end_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total = db.execute(count_query).scalar_one()

    page = max(1, page)
    page_size = min(100, max(1, page_size))
    total_pages = ceil(total / page_size) if total > 0 else 1

    items = db.execute(
        query.order_by(MarketDemand.period_start_date.desc(), MarketDemand.id.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
    ).scalars().all()

    return PaginatedMarketDemandResponse(
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        ),
        items=[MarketDemandResponse.model_validate(it) for it in items]
    )


def delete_market_demand(db: Session, demand_id: int) -> bool:
    """Delete a market demand entry by ID."""
    record = get_market_demand(db, demand_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True
