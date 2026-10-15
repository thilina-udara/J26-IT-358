from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_admin_access
from app.schemas.cultivation_cost import CultivationBudgetCreate, CultivationBudgetResponse, PaginatedCultivationBudgetResponse
from app.services.cultivation_budget_service import (
    create_cultivation_budget,
    get_cultivation_budget,
    list_cultivation_budgets,
    delete_cultivation_budget,
)

router = APIRouter()


@router.post(
    "",
    response_model=CultivationBudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a farmer cultivation budget",
    description="Save a cultivation budget supporting both 'quick' (total only) and 'detailed' (itemized categories) entry modes."
)
def create_budget_endpoint(
    payload: CultivationBudgetCreate,
    db: Session = Depends(get_db)
):
    return create_cultivation_budget(db, payload)


@router.get(
    "",
    response_model=PaginatedCultivationBudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="List cultivation budgets with filtering and pagination (Authorized)",
    description=(
        "Retrieve cultivation budgets filtered by crop, district, season, year, and entry mode. "
        "Temporarily restricted to authorized administrative access to protect farmer financial privacy "
        "and prevent unauthenticated snooping. Proper farmer authentication and ownership-based access "
        "control are required before public deployment."
    )
)
def list_budgets_endpoint(
    crop_id: Optional[str] = Query(None, description="Crop identifier (e.g., 'red_onion')"),
    district_id: Optional[str] = Query(None, description="District code (e.g., 'LK-71')"),
    season: Optional[str] = Query(None, description="Agrarian season ('Maha', 'Yala', 'Year-round')"),
    year: Optional[int] = Query(None, description="Agrarian calendar year"),
    entry_mode: Optional[str] = Query(None, description="Budget entry mode ('quick' or 'detailed')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    return list_cultivation_budgets(
        db=db,
        crop_id=crop_id,
        district_id=district_id,
        season=season,
        year=year,
        entry_mode=entry_mode,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{budget_id}",
    response_model=CultivationBudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual cultivation budget (Authorized)",
    description=(
        "Fetch a specific cultivation budget by primary key ID. Temporarily restricted to authorized "
        "administrative access to prevent unauthenticated enumeration of farmer cost records. "
        "Proper farmer authentication and ownership-based access control are required before public deployment."
    )
)
def get_budget_endpoint(
    budget_id: int,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    record = get_cultivation_budget(db, budget_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cultivation budget with ID {budget_id} not found."
        )
    return record


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cultivation budget (Admin)",
    description="Permanently remove a cultivation budget record. Requires administrative authorization to prevent accidental budget deletion."
)
def delete_budget_endpoint(
    budget_id: int,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    success = delete_cultivation_budget(db, budget_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cultivation budget with ID {budget_id} not found."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
