"""
Component 3: Algorithmic Optimization of Circular Bioeconomy Networks (Waste Management & Organic Fertilizer)
Owner: WMK Lakruwan (IT23330382)
Project: J26-IT-358
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Algorithmic Optimization of Circular Bioeconomy Networks",
    description="Microservice for post-harvest spoilage risk scoring, MILP C:N compost ratio optimization, and NPK redistribution.",
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
        "service": "Algorithmic Optimization of Circular Bioeconomy Networks",
        "component": "Component 03",
        "owner": "WMK Lakruwan",
        "status": "online",
        "port": 8003
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "waste-bioeconomy-service"}
