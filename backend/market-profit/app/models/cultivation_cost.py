from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CultivationBudget(Base):
    """
    Cultivation cost budget for a crop and agrarian season.
    Supports both 'quick' (total-cost only) and 'detailed' (itemized categories) entry modes.
    Unprovided categories in quick mode remain null rather than zero.
    """
    __tablename__ = "cultivation_budgets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    crop_id = Column(String(32), nullable=False, index=True)
    district_id = Column(String(10), nullable=False, index=True)
    season = Column(String(20), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    entry_mode = Column(String(20), nullable=False, default="detailed")
    land_extent_acres = Column(Numeric(8, 2), nullable=False, default=1.00)
    total_cost = Column(Numeric(12, 2), nullable=False)

    # Breakdown categories: nullable to preserve distinction between null and zero expenditure
    land_preparation_cost = Column(Numeric(12, 2), nullable=True)
    seeds_plants_cost = Column(Numeric(12, 2), nullable=True)
    fertilizer_cost = Column(Numeric(12, 2), nullable=True)
    pesticide_weedicide_cost = Column(Numeric(12, 2), nullable=True)
    labor_cost = Column(Numeric(12, 2), nullable=True)
    machinery_fuel_cost = Column(Numeric(12, 2), nullable=True)
    transport_packaging_cost = Column(Numeric(12, 2), nullable=True)
    miscellaneous_cost = Column(Numeric(12, 2), nullable=True)

    expected_yield_kg = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="kg")
    currency = Column(String(10), nullable=False, default="LKR")
    data_source = Column(String(100), nullable=False, default="Farmer Reported")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    analyses = relationship("MarketProfitAnalysis", back_populates="cultivation_budget", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_cultivation_budgets_crop_district_season", "crop_id", "district_id", "season", "year"),
    )

    def __repr__(self) -> str:
        return (
            f"<CultivationBudget(id={self.id}, crop_id='{self.crop_id}', district_id='{self.district_id}', "
            f"season='{self.season} {self.year}', mode='{self.entry_mode}', total_cost={self.total_cost} {self.currency})>"
        )
