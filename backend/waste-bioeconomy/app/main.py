"""
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks (Waste Management & Organic Fertilizer)
Owner: WMK Lakruwan (IT23330382)
Project: J26-IT-358
Supervised by: Prof. Dasuni Nawinna
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.compost import router as compost_router
from app.routes.fertilizer import router as fertilizer_router
from app.routes.risk import router as risk_router

app = FastAPI(
    title="Algorithmic Optimization of Circular Bioeconomy Networks",
    description=(
        "Research microservice for pre-arrival post-harvest spoilage risk scoring (XGBoost), "
        "dual-stream commercial/bioeconomy mass partitioning, Mixed-Integer Linear Programming (MILP) "
        "compost C:N & moisture recipe optimization (PuLP/HiGHS), SLSI 1246:2003 quality certification audits, "
        "automated anaerobic biogas fallback routing, and closed-loop NPK fertilizer demand matching with CVRP routing."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration for Frontend Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Subsystem Routers
app.include_router(risk_router)
app.include_router(compost_router)
app.include_router(fertilizer_router)


@app.get("/", tags=["System Information"])
def root() -> dict[str, str | int]:
    return {
        "service": "Algorithmic Optimization of Circular Bioeconomy Networks",
        "component": "Component 03",
        "owner": "WMK Lakruwan (IT23330382)",
        "project": "J26-IT-358",
        "status": "online",
        "port": 8003,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System Information"])
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "waste-bioeconomy-service",
        "component": "Component 03",
        "ml_engine": "XGBoost v3.4.1",
        "optimizer_engine": "PuLP MILP + HiGHS / SciPy Simplex",
    }
