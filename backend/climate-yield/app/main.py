"""
Climate & Crop Yield Decision Support Microservice
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.yield_prediction import router as yield_prediction_router

app = FastAPI(
    title="AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System",
    description="Comprehensive decision support system integrating 14-day forward climate hazard screening, crop phenological vulnerability assessment, seasonal yield deficit forecasting, and Linear SHAP explainability across all 25 districts of Sri Lanka for 7 approved crops.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Prediction & Early Warning Router
app.include_router(yield_prediction_router)


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
