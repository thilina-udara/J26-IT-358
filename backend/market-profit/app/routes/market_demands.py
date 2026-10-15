from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_admin_access
from app.schemas.market_demand import MarketDemandCreate, MarketDemandResponse, PaginatedMarketDemandResponse
from app.services.market_demand_service import (
    create_market_demand,
    get_market_demand,
    list_market_demands,
    delete_market_demand,
)

router = APIRouter()


@router.post(
    "",
    response_model=MarketDemandResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a commodity market demand record (Admin)",
    description="Record an observed, estimated, or synthetic market demand entry. Requires administrative authorization. Synthetic records are automatically marked non-training eligible."
)
def create_demand_endpoint(
    payload: MarketDemandCreate,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    return create_market_demand(db, payload)


@router.get(
    "",
    response_model=PaginatedMarketDemandResponse,
    status_code=status.HTTP_200_OK,
    summary="List market demand records with filtering and pagination",
    description="Retrieve demand records filtered by crop, district, market center, record type, demand level, and date period."
)
def list_demands_endpoint(
    crop_id: Optional[str] = Query(None, description="Crop identifier (e.g., 'chilli')"),
    district_id: Optional[str] = Query(None, description="District code (e.g., 'LK-71')"),
    market_id: Optional[str] = Query(None, description="Market identifier (e.g., 'DEC_DAMBULLA')"),
    record_type: Optional[str] = Query(None, description="Record type ('observed', 'estimated', 'synthetic')"),
    demand_level: Optional[str] = Query(None, description="Demand level ('High', 'Medium', 'Low')"),
    is_training_eligible: Optional[bool] = Query(None, description="Filter by ML training eligibility flag"),
    start_date: Optional[date] = Query(None, description="Earliest period start date"),
    end_date: Optional[date] = Query(None, description="Latest period end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date."
        )
    return list_market_demands(
        db=db,
        crop_id=crop_id,
        district_id=district_id,
        market_id=market_id,
        record_type=record_type,
        demand_level=demand_level,
        is_training_eligible=is_training_eligible,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{demand_id}",
    response_model=MarketDemandResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual market demand record",
    description="Fetch a specific demand entry by primary key ID."
)
def get_demand_endpoint(
    demand_id: int,
    db: Session = Depends(get_db)
):
    record = get_market_demand(db, demand_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market demand record with ID {demand_id} not found."
        )
    return record


@router.delete(
    "/{demand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a market demand record (Admin)",
    description="Permanently remove a market demand entry. Restricted to administrative users."
)
def delete_demand_endpoint(
    demand_id: int,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    success = delete_market_demand(db, demand_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market demand record with ID {demand_id} not found."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
