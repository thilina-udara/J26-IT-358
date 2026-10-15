from math import ceil
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.models.cultivation_cost import CultivationBudget
from app.schemas.cultivation_cost import CultivationBudgetCreate, PaginatedCultivationBudgetResponse, CultivationBudgetResponse
from app.schemas.common import BudgetEntryMode, PaginationMeta


def create_cultivation_budget(db: Session, data: CultivationBudgetCreate) -> CultivationBudget:
    """
    Create a new farmer cultivation budget record.
    Supports:
    - Quick mode: only total_cost is specified, category breakdowns remain None (SQL NULL).
    - Detailed mode: category breakdown is specified, total_cost is verified or auto-computed.
    """
    land_prep = None
    seeds = None
    fertilizer = None
    pesticide = None
    labor = None
    machinery = None
    transport = None
    misc = None

    if data.entry_mode == BudgetEntryMode.DETAILED and data.breakdown:
        land_prep = data.breakdown.land_preparation_cost
        seeds = data.breakdown.seeds_plants_cost
        fertilizer = data.breakdown.fertilizer_cost
        pesticide = data.breakdown.pesticide_weedicide_cost
        labor = data.breakdown.labor_cost
        machinery = data.breakdown.machinery_fuel_cost
        transport = data.breakdown.transport_packaging_cost
        misc = data.breakdown.miscellaneous_cost

    budget = CultivationBudget(
        crop_id=data.crop_id,
        district_id=data.district_id,
        season=data.season.value,
        year=data.year,
        entry_mode=data.entry_mode.value,
        land_extent_acres=data.land_extent_acres,
        total_cost=data.total_cost,
        land_preparation_cost=land_prep,
        seeds_plants_cost=seeds,
        fertilizer_cost=fertilizer,
        pesticide_weedicide_cost=pesticide,
        labor_cost=labor,
        machinery_fuel_cost=machinery,
        transport_packaging_cost=transport,
        miscellaneous_cost=misc,
        expected_yield_kg=data.expected_yield_kg,
        unit=data.unit,
        currency=data.currency,
        data_source=data.data_source,
        notes=data.notes
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def get_cultivation_budget(db: Session, budget_id: int) -> Optional[CultivationBudget]:
    """Retrieve an individual cultivation budget by ID."""
    return db.execute(
        select(CultivationBudget).where(CultivationBudget.id == budget_id)
    ).scalar_one_or_none()


def list_cultivation_budgets(
    db: Session,
    crop_id: Optional[str] = None,
    district_id: Optional[str] = None,
    season: Optional[str] = None,
    year: Optional[int] = None,
    entry_mode: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
) -> PaginatedCultivationBudgetResponse:
    """Query cultivation budgets with filtering and pagination."""
    query = select(CultivationBudget)
    count_query = select(func.count(CultivationBudget.id))

    filters = []
    if crop_id:
        filters.append(CultivationBudget.crop_id == crop_id)
    if district_id:
        filters.append(CultivationBudget.district_id == district_id)
    if season:
        filters.append(CultivationBudget.season == season)
    if year:
        filters.append(CultivationBudget.year == year)
    if entry_mode:
        filters.append(CultivationBudget.entry_mode == entry_mode)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total = db.execute(count_query).scalar_one()

    page = max(1, page)
    page_size = min(100, max(1, page_size))
    total_pages = ceil(total / page_size) if total > 0 else 1

    items = db.execute(
        query.order_by(CultivationBudget.year.desc(), CultivationBudget.id.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
    ).scalars().all()

    return PaginatedCultivationBudgetResponse(
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        ),
        items=[CultivationBudgetResponse.model_validate(it) for it in items]
    )


def delete_cultivation_budget(db: Session, budget_id: int) -> bool:
    """Delete a cultivation budget record by ID."""
    record = get_cultivation_budget(db, budget_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True
