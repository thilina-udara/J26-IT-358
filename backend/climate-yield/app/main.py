"""
Component 4: AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System
Deshapriya P.D.T.U (IT23247086)
Project: J26-IT-358
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System",
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
        "service": "AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System",
        "component": "Component 04",
        "lead": "Deshapriya P.D.T.U",
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
        "component_name": "AI-Powered Climate Early Warning and Crop Yield Impact Decision Support System",
        "supported_models": ["XGBoost", "LightGBM", "LSTM"],
        "explainability": "TreeSHAP",
        "data_sources": ["NASA POWER API", "Copernicus ERA5-Land", "DCS / HARTI Historical Statistics"],
        "spatial_coverage": "25 Districts of Sri Lanka"
    }
