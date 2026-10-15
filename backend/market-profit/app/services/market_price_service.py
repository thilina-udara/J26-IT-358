from datetime import date
from math import ceil
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.models.market_price import MarketPrice
from app.schemas.market_price import MarketPriceCreate, PaginatedMarketPriceResponse, MarketPriceResponse
from app.schemas.common import PaginationMeta


def create_market_price(db: Session, data: MarketPriceCreate) -> MarketPrice:
    """Create a new historical market price observation. Rejects duplicates with 409 Conflict."""
    existing = db.execute(
        select(MarketPrice).where(
            and_(
                MarketPrice.crop_id == data.crop_id,
                MarketPrice.market_id == data.market_id,
                MarketPrice.price_date == data.price_date,
                MarketPrice.price_type == data.price_type.value,
                MarketPrice.price_grade == data.price_grade
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A price observation already exists for crop '{data.crop_id}' at market '{data.market_id}' "
                f"on {data.price_date} (Type: {data.price_type.value}, Grade: {data.price_grade})."
            )
        )

    price_record = MarketPrice(
        crop_id=data.crop_id,
        market_id=data.market_id,
        market_name=data.market_name,
        district_id=data.district_id,
        price_date=data.price_date,
        price_type=data.price_type.value,
        price=data.price,
        unit=data.unit,
        currency=data.currency,
        volume_traded_kg=data.volume_traded_kg,
        price_grade=data.price_grade,
        data_source=data.data_source,
        data_quality_flag=data.data_quality_flag,
        notes=data.notes
    )
    db.add(price_record)
    db.commit()
    db.refresh(price_record)
    return price_record


def get_market_price(db: Session, price_id: int) -> Optional[MarketPrice]:
    """Retrieve an individual market price record by ID."""
    return db.execute(
        select(MarketPrice).where(MarketPrice.id == price_id)
    ).scalar_one_or_none()


def list_market_prices(
    db: Session,
    crop_id: Optional[str] = None,
    market_id: Optional[str] = None,
    district_id: Optional[str] = None,
    price_type: Optional[str] = None,
    price_grade: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 50
) -> PaginatedMarketPriceResponse:
    """Query historical market price records with multi-attribute filtering and pagination."""
    query = select(MarketPrice)
    count_query = select(func.count(MarketPrice.id))

    filters = []
    if crop_id:
        filters.append(MarketPrice.crop_id == crop_id)
    if market_id:
        filters.append(MarketPrice.market_id == market_id)
    if district_id:
        filters.append(MarketPrice.district_id == district_id)
    if price_type:
        filters.append(MarketPrice.price_type == price_type)
    if price_grade:
        filters.append(MarketPrice.price_grade == price_grade)
    if start_date:
        filters.append(MarketPrice.price_date >= start_date)
    if end_date:
        filters.append(MarketPrice.price_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total = db.execute(count_query).scalar_one()

    # Pagination bounds
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    total_pages = ceil(total / page_size) if total > 0 else 1

    items = db.execute(
        query.order_by(MarketPrice.price_date.desc(), MarketPrice.id.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
    ).scalars().all()

    return PaginatedMarketPriceResponse(
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        ),
        items=[MarketPriceResponse.model_validate(it) for it in items]
    )


def delete_market_price(db: Session, price_id: int) -> bool:
    """Delete a market price record by ID."""
    record = get_market_price(db, price_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True
