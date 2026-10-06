import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Locate root .env file (two levels up from backend/climate-yield/)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "AgriDecision-LK (Component 4: Climate & Yield)"
    
    # Shared PostgreSQL + PostGIS Database (strictly loaded from .env)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    DATABASE_URL: str | None = None
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # External APIs (Component 4)
    NASA_POWER_API_BASE: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    COPERNICUS_CDS_API_KEY: str = ""

    def get_database_url(self) -> str:
        """Construct database URL securely from environment settings."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if not self.POSTGRES_USER or not self.POSTGRES_PASSWORD or not self.POSTGRES_DB:
            raise ValueError(
                "Database configuration missing: POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB "
                "must be specified in your local .env file."
            )
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = str(ENV_PATH) if ENV_PATH.exists() else ".env"
        extra = "allow"

settings = Settings()
