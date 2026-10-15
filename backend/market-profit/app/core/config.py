from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate repository root .env file relative to this source file
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parents[4] if len(CURRENT_FILE.parents) >= 5 else CURRENT_FILE.parent
ENV_PATH = ROOT_DIR / ".env"


def normalize_database_url(url: str) -> str:
    """
    Normalize a PostgreSQL connection string to explicitly use the psycopg2 driver
    dialect (postgresql+psycopg2://) without altering credentials, host, or query parameters.
    """
    if not url:
        return url

    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    return url


class Settings(BaseSettings):
    """Application settings for Market Profit microservice."""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "AgriSense - Market Demand, Price Trend and Profit Risk Prediction"

    # PostgreSQL configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    DATABASE_URL: str | None = None

    # Microservice configuration
    PORT_MARKET_PROFIT_SERVICE: int = 8001

    # Administrative Security & Access Control (loaded strictly from environment configuration)
    ADMIN_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        """
        Construct or normalize the PostgreSQL database URL using the psycopg2 dialect.
        Ensures credentials are not exposed or logged.
        """
        if self.DATABASE_URL:
            return normalize_database_url(self.DATABASE_URL)

        if not self.POSTGRES_USER or not self.POSTGRES_PASSWORD or not self.POSTGRES_DB:
            raise ValueError(
                "Database configuration missing: DATABASE_URL or POSTGRES_USER, "
                "POSTGRES_PASSWORD, and POSTGRES_DB must be configured in .env."
            )

        raw_url = (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        return normalize_database_url(raw_url)


settings = Settings()
