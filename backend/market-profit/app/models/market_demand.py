from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Index, Numeric, String, Text, func
from app.core.database import Base


class MarketDemand(Base):
    """
    Market demand record storing observed, estimated, or synthetic commodity demand.
    Explicitly tracks provenance and marks training eligibility to prevent data contamination.
    """
    __tablename__ = "market_demand_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    crop_id = Column(String(32), nullable=False, index=True)
    district_id = Column(String(10), nullable=False, index=True)
    market_id = Column(String(50), nullable=True, index=True)
    period_start_date = Column(Date, nullable=False, index=True)
    period_end_date = Column(Date, nullable=False, index=True)
    demand_volume_kg = Column(Numeric(14, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="kg")
    record_type = Column(String(20), nullable=False, index=True)
    demand_level = Column(String(10), nullable=True)
    confidence_score = Column(Numeric(4, 3), nullable=True)
    estimation_method = Column(String(100), nullable=True)
    is_training_eligible = Column(Boolean, nullable=False, default=True)
    data_source = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_market_demand_crop_district_date", "crop_id", "district_id", "period_start_date"),
        Index("ix_market_demand_type_eligible", "record_type", "is_training_eligible"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketDemand(id={self.id}, crop_id='{self.crop_id}', district_id='{self.district_id}', "
            f"period={self.period_start_date}..{self.period_end_date}, "
            f"volume={self.demand_volume_kg} {self.unit}, type='{self.record_type}')>"
        )
