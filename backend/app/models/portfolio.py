"""
Modèles SQLAlchemy — Portefeuilles, positions, transactions, historique prix.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date, DateTime, Float, ForeignKey,
    Integer, Numeric, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base
from app.models.user import generate_uuid


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capital: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    user: Mapped["user.User"] = relationship(back_populates="portfolios")
    holdings: Mapped[list["Holding"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} name={self.name}>"


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_buy_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weight_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # % du portefeuille

    # Relations
    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")

    def __repr__(self) -> str:
        return f"<Holding {self.ticker} qty={self.quantity} weight={self.weight_pct:.1%}>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)   # buy / sell
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    portfolio: Mapped["Portfolio"] = relationship(back_populates="transactions")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=True)
    high: Mapped[float] = mapped_column(Float, nullable=True)
    low: Mapped[float] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        # Contrainte d'unicité ticker + date
        __import__("sqlalchemy").UniqueConstraint("ticker", "date", name="uq_price_history_ticker_date"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory {self.ticker} {self.date} close={self.close}>"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    shap_data: Mapped[dict] = mapped_column(__import__("sqlalchemy").JSON, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    final_allocation: Mapped[dict] = mapped_column(__import__("sqlalchemy").JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    portfolio: Mapped["Portfolio"] = relationship(back_populates="recommendations")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)       # "drift", "threshold", etc.
    threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_read: Mapped[bool] = mapped_column(default=False)

    # Relations
    portfolio: Mapped["Portfolio"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert type={self.type} read={self.is_read}>"
