"""
Component 2: AI-Based Cultivation Concentration Risk Analysis, Alternative Crop Recommendation, and Personalized Cultivation Planning System
Owner: Uthpala G.D. (IT23223080)
Project: J26-IT-358
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI-Based Cultivation Concentration Risk Analysis and Planning System",
    description="Microservice for spatial-temporal clustering of crop concentration, oversupply warning, and alternative crop planning.",
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
        "service": "AI-Based Cultivation Concentration Risk Analysis",
        "component": "Component 02",
        "owner": "Uthpala G.D.",
        "status": "online",
        "port": 8002
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "cultivation-concentration-service"}
