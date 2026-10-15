from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_admin_access
from app.schemas.market_price import MarketPriceCreate, MarketPriceResponse, PaginatedMarketPriceResponse
from app.schemas.price_forecast import PriceForecastRequest, PriceForecastResponse
from app.services.market_price_service import (
    create_market_price,
    get_market_price,
    list_market_prices,
    delete_market_price,
)
from app.services.price_forecasting_service import AbstractPricePredictor, get_price_predictor

router = APIRouter()


@router.post(
    "",
    response_model=MarketPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a historical market price observation (Admin)",
    description="Record a new wholesale or retail commodity price observation. Requires administrative authorization to prevent unauthorized historical data manipulation."
)
def create_price_endpoint(
    payload: MarketPriceCreate,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    return create_market_price(db, payload)


@router.post(
    "/forecast",
    response_model=PriceForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Stateless ML-ready commodity price trend forecasting",
    description=(
        "Generate a forecasted price per kg (LKR) for a given crop, cultivation district, "
        "target market center, arrival date, and price type (wholesale or retail). "
        "Returns prediction_status='unavailable' until trained machine-learning models are connected. "
        "This endpoint is entirely stateless and does not persist records to PostgreSQL."
    )
)
def forecast_price_endpoint(
    payload: PriceForecastRequest,
    predictor: AbstractPricePredictor = Depends(get_price_predictor)
) -> PriceForecastResponse:
    return predictor.forecast_price(payload)


@router.get(
    "",
    response_model=PaginatedMarketPriceResponse,
    status_code=status.HTTP_200_OK,
    summary="List historical market prices with filtering and pagination",
    description="Retrieve price observations filtered by crop, market center, district, price type, grade, and date window."
)
def list_prices_endpoint(
    crop_id: Optional[str] = Query(None, description="Crop identifier (e.g., 'red_onion')"),
    market_id: Optional[str] = Query(None, description="Market identifier (e.g., 'DEC_DAMBULLA')"),
    district_id: Optional[str] = Query(None, description="District code (e.g., 'LK-71')"),
    price_type: Optional[str] = Query(None, description="Price type ('wholesale' or 'retail')"),
    price_grade: Optional[str] = Query(None, description="Quality grade ('Grade 1', etc.)"),
    start_date: Optional[date] = Query(None, description="Earliest observation date"),
    end_date: Optional[date] = Query(None, description="Latest observation date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date."
        )
    return list_market_prices(
        db=db,
        crop_id=crop_id,
        market_id=market_id,
        district_id=district_id,
        price_type=price_type,
        price_grade=price_grade,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{price_id}",
    response_model=MarketPriceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an individual market price record",
    description="Fetch a specific historical price record by primary key ID."
)
def get_price_endpoint(
    price_id: int,
    db: Session = Depends(get_db)
):
    record = get_market_price(db, price_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market price record with ID {price_id} not found."
        )
    return record


@router.delete(
    "/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a market price record (Admin)",
    description="Permanently remove a historical price record. Restricted to administrative users to prevent accidental or malicious data loss."
)
def delete_price_endpoint(
    price_id: int,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_admin_access)
):
    success = delete_market_price(db, price_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market price record with ID {price_id} not found."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
