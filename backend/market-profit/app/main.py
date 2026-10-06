"""
Component 1: Market Demand, Price Trend and Profit Risk Prediction
Owner: Ranadewa H.D.D.C.S (IT23159594)
Project: J26-IT-358
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
