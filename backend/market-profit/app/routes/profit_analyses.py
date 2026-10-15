from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_admin_access
from app.schemas.profit_analysis import FarmerAnalysisInput, PaginatedProfitAnalysisResponse, PredictionResultResponse
from app.services.profit_analysis_service import (
    create_profit_analysis,
    get_profit_analysis,
    list_profit_analyses,
    delete_profit_analysis,
    format_profit_analysis_response,
)

router = APIRouter()


@router.post(
    "",
    response_model=PredictionResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create market-profit analysis request",
    description="Register farmer cultivation and market arrival parameters. Returns explicit model-unavailable status until ML inference is active."
)
def create_analysis_endpoint(
    payload: FarmerAnalysisInput,
    db: Session = Depends(get_db)
):
    record = create_profit_analysis(db, payload)
    return format_profit_analysis_response(record)


@router.get(
    "",
    response_model=PaginatedProfitAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="List saved profit analyses with filtering and pagination (Authorized)",
    description=(
        "Retrieve saved analyses filtered by crop, district, market center, status, risk level, and target arrival date. "
        "Temporarily restricted to authorized administrative access to protect sensitive farmer economic and crop planning data. "
        "Proper farmer authentication and ownership-based access control are required before public deployment."
    )
)
def list_analyses_endpoint(
    crop_id: Optional[str] = Query(None, description="Crop identifier (e.g., 'red_onion')"),
    cultivation_district_id: Optional[str] = Query(None, description="Cultivation district code (e.g., 'LK-71')"),
    target_market_id: Optional[str] = Query(None, description="Selling market identifier (e.g., 'DEC_DAMBULLA')"),
    prediction_status: Optional[str] = Query(None, description="Prediction lifecycle status ('pending', 'completed', 'unavailable', 'failed')"),
    profit_risk_level: Optional[str] = Query(None, description="Assessed profit risk level ('Low', 'Medium', 'High')"),
    start_date: Optional[date] = Query(None, description="Earliest forecast target date"),
    end_date: Optional[date] = Query(None, description="Latest forecast target date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date."
        )
    return list_profit_analyses(
        db=db,
        crop_id=crop_id,
        cultivation_district_id=cultivation_district_id,
        target_market_id=target_market_id,
        prediction_status=prediction_status,
        profit_risk_level=profit_risk_level,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{analysis_id}",
    response_model=PredictionResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual profit analysis (Authorized)",
    description=(
        "Fetch a specific analysis record by primary key ID or unique analysis reference string (e.g., 'REF-XXXX'). "
        "Temporarily restricted to authorized administrative access to prevent unauthorized lookup or enumeration of farmer assessments. "
        "Proper farmer authentication and ownership-based access control are required before public deployment."
    )
)
def get_analysis_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    record = get_profit_analysis(db, analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profit analysis record '{analysis_id}' not found."
        )
    return format_profit_analysis_response(record)


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a profit analysis record (Admin)",
    description="Permanently remove a saved analysis record by primary key ID or analysis reference string. Requires administrative authorization to prevent accidental loss of saved farmer assessments."
)
def delete_analysis_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    success = delete_profit_analysis(db, analysis_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profit analysis record '{analysis_id}' not found."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
