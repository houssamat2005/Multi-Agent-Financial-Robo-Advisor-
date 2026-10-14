"""
Routes backtesting — GET /portfolio/{id}/backtest
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.postgres import get_db
from app.models.portfolio import Portfolio, Holding
from app.models.user import User, RiskProfile
from app.services.backtesting import run_backtest, BacktestError

router = APIRouter()


@router.get("/{portfolio_id}/backtest", summary="Backtesting de la stratégie Markowitz")
async def backtest_portfolio(
    portfolio_id: str,
    start: Optional[str] = Query(default="2020-01-01", description="Date de début (YYYY-MM-DD)"),
    end: Optional[str] = Query(default="2024-12-31", description="Date de fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Backteste la stratégie Markowitz sur données historiques.
    Compare avec le S&P 500 (SPY) comme benchmark.
    Cible : Sharpe Ratio > 1.0 sur 2020–2024.
    """
    # Vérifier le portefeuille
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portefeuille introuvable.")

    # Parser les dates
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        if start_date >= end_date:
            raise ValueError
        if end_date > date.today():
            end_date = date.today()
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Dates invalides. Format : YYYY-MM-DD. La date de début doit être avant la date de fin."
        )

    # Tickers du portefeuille
    holdings_result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    holdings = holdings_result.scalars().all()
    tickers = [h.ticker for h in holdings] if holdings else ["AAPL", "MSFT", "GOOGL", "AMZN", "SPY"]

    # Profil de risque
    profile_result = await db.execute(
        select(RiskProfile)
        .where(RiskProfile.user_id == current_user.id)
        .order_by(RiskProfile.created_at.desc())
        .limit(1)
    )
    risk_profile_obj = profile_result.scalar_one_or_none()
    risk_profile = risk_profile_obj.profile_type if risk_profile_obj else "modéré"

    try:
        metrics = await run_backtest(
            tickers=tickers,
            risk_profile=risk_profile,
            start_date=start_date,
            end_date=end_date,
        )
        return metrics

    except BacktestError as e:
        raise HTTPException(status_code=422, detail=str(e))
