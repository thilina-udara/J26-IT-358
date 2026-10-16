"""
Climate & Crop Yield Decision Support Microservice
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Climate-Yield Decision Support Service",
    description="Microservice for meteorological hazard monitoring, pre-harvest crop yield deficit prediction, and TreeSHAP explainability.",
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
        "service": "climate-yield-service",
        "status": "online",
        "port": 8004,
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "climate-yield-service"}

@app.get("/api/v1/info")
def get_component_info():
    return {
        "service_name": "Climate-Yield Decision Support Service",
        "supported_models": ["Adaptive Hybrid AI", "XGBoost"],
        "explainability": "TreeSHAP",
        "data_sources": ["NASA POWER API", "Copernicus ERA5-Land", "DCS Historical Statistics"],
        "spatial_coverage": "25 Districts of Sri Lanka"
    }
