from sqlalchemy import BigInteger, Column, Date, DateTime, Index, Numeric, String, Text, UniqueConstraint, func
from app.core.database import Base


class MarketPrice(Base):
    """
    Historical commodity market price observation at Sri Lankan Dedicated Economic
    Centres (DECs) or local markets. Supports incomplete observations without fabricating values.
    """
    __tablename__ = "market_prices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    crop_id = Column(String(32), nullable=False, index=True)
    market_id = Column(String(50), nullable=False, index=True)
    market_name = Column(String(100), nullable=False)
    district_id = Column(String(10), nullable=True, index=True)
    price_date = Column(Date, nullable=False, index=True)
    price_type = Column(String(20), nullable=False, default="wholesale")
    price = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="kg")
    currency = Column(String(10), nullable=False, default="LKR")
    volume_traded_kg = Column(Numeric(12, 2), nullable=True)
    price_grade = Column(String(20), nullable=True, default="Standard")
    data_source = Column(String(100), nullable=False)
    data_quality_flag = Column(String(30), nullable=False, default="verified")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "crop_id", "market_id", "price_date", "price_type", "price_grade",
            name="uq_market_price_entry"
        ),
        Index("ix_market_prices_crop_date", "crop_id", "price_date"),
        Index("ix_market_prices_market_date", "market_id", "price_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketPrice(id={self.id}, crop_id='{self.crop_id}', market_id='{self.market_id}', "
            f"price_date={self.price_date}, price={self.price} {self.currency}/{self.unit})>"
        )
