from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class MarketProfitAnalysis(Base):
    """
    Saved prediction and decision analysis result.
    Separates cultivation district from selling market.
    ML-dependent predictions are fully nullable until actual inference completes.
    Tracks prediction status across pending, completed, unavailable, and failed states.
    """
    __tablename__ = "market_profit_analyses"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    analysis_reference = Column(String(64), unique=True, index=True, nullable=False)
    crop_id = Column(String(32), nullable=False, index=True)
    cultivation_district_id = Column(String(10), nullable=False, index=True)
    target_market_id = Column(String(50), nullable=False, index=True)
    target_market_name = Column(String(100), nullable=True)
    cultivation_budget_id = Column(BigInteger, ForeignKey("cultivation_budgets.id", ondelete="SET NULL"), nullable=True)

    # Lifecycle state
    prediction_status = Column(String(20), nullable=False, default="pending", index=True)

    # Input planning parameters
    forecast_target_date = Column(Date, nullable=False, index=True)
    forecast_horizon_days = Column(Integer, nullable=False, default=90)
    cultivation_extent_acres = Column(Numeric(8, 2), nullable=False)
    estimated_production_kg = Column(Numeric(12, 2), nullable=False)
    estimated_total_cost = Column(Numeric(12, 2), nullable=False)

    # ML-dependent forecasted outputs (strictly nullable when pending, unavailable, or failed)
    forecasted_wholesale_price = Column(Numeric(10, 2), nullable=True)
    price_confidence_lower = Column(Numeric(10, 2), nullable=True)
    price_confidence_upper = Column(Numeric(10, 2), nullable=True)
    projected_demand_volume_kg = Column(Numeric(14, 2), nullable=True)
    projected_demand_level = Column(String(10), nullable=True)
    projected_revenue = Column(Numeric(12, 2), nullable=True)
    projected_net_profit = Column(Numeric(12, 2), nullable=True)
    projected_roi_percentage = Column(Numeric(6, 2), nullable=True)
    profit_risk_level = Column(String(10), nullable=True, index=True)
    risk_score = Column(Numeric(5, 4), nullable=True)
    risk_factors = Column(JSON, nullable=True)

    # ML model provenance & error diagnosis (agnostic of specific algorithms)
    model_version = Column(String(50), nullable=True)
    model_provenance = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    cultivation_budget = relationship("CultivationBudget", back_populates="analyses")

    __table_args__ = (
        Index("ix_profit_analysis_crop_market_date", "crop_id", "target_market_id", "forecast_target_date"),
        Index("ix_profit_analysis_status", "prediction_status", "profit_risk_level"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketProfitAnalysis(id={self.id}, ref='{self.analysis_reference}', "
            f"crop='{self.crop_id}', market='{self.target_market_id}', "
            f"status='{self.prediction_status}', risk='{self.profit_risk_level}')>"
        )
