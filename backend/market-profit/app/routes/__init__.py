from fastapi import APIRouter
from app.routes.market_prices import router as market_prices_router
from app.routes.market_demands import router as market_demands_router
from app.routes.cultivation_budgets import router as cultivation_budgets_router
from app.routes.profit_analyses import router as profit_analyses_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(
    market_prices_router,
    prefix="/market-prices",
    tags=["Market Prices"]
)

api_router.include_router(
    market_demands_router,
    prefix="/market-demands",
    tags=["Market Demands"]
)

api_router.include_router(
    cultivation_budgets_router,
    prefix="/cultivation-budgets",
    tags=["Cultivation Budgets"]
)

api_router.include_router(
    profit_analyses_router,
    prefix="/profit-analyses",
    tags=["Market-Profit Analyses"]
)

__all__ = ["api_router"]
