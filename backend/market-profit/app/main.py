"""
Component 1: Market Demand, Price Trend and Profit Risk Prediction
Owner: Ranadewa H.D.D.C.S (IT23159594)
Project: J26-IT-358
"""

import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Market Demand, Price Trend and Profit Risk Prediction",
    description="Microservice for harvest price trend forecasting, SEPC cultivation budgeting, and profit risk classification.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "service": "Market Demand, Price Trend and Profit Risk Prediction",
        "component": "Component 01",
        "owner": "Ranadewa H.D.D.C.S",
        "status": "online",
        "port": 8001
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "market-profit-service"}

@app.get("/health/db")
def database_health_check():
    """
    Verify PostgreSQL database connectivity using a read-only SELECT 1 query.
    Returns 200 OK when database is accessible, or 503 Service Unavailable on failure.
    Internal connection strings, credentials, or traces are strictly excluded from responses.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "market-profit-service",
            "database": "connected"
        }
    except Exception as exc:
        logger.error("Database health check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
