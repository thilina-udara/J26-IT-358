from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Create SQLAlchemy engine connected to PostgreSQL + PostGIS
engine = create_engine(
    settings.get_database_url(),
    pool_pre_ping=True,       # Automatically check connection validity
    pool_size=10,             # Keep up to 10 persistent connections
    max_overflow=20           # Allow up to 20 burst connections under load
)

# Session factory for handling database transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for all SQLAlchemy ORM models
Base = declarative_base()

# FastAPI dependency to get a database session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
