"""
Service Backtesting — vectorbt.
Valide la stratégie Markowitz sur données historiques.
Benchmark : S&P 500 (SPY).
"""
import logging
from datetime import date

import numpy as np
import pandas as pd

from app.core.config import settings
from app.db.postgres import AsyncSessionLocal
from app.models.portfolio import PriceHistory
from sqlalchemy import select, and_

log = logging.getLogger(__name__)


class BacktestError(Exception):
    pass


async def _get_prices_for_backtest(
    tickers: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Charge les prix depuis PostgreSQL pour la fenêtre de backtest."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PriceHistory.date, PriceHistory.ticker, PriceHistory.close)
            .where(
                PriceHistory.ticker.in_(tickers),
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date,
            )
            .order_by(PriceHistory.date)
        )
        rows = result.fetchall()

    if not rows:
        raise BacktestError(f"Pas de données pour {tickers} entre {start_date} et {end_date}")

    df = pd.DataFrame(rows, columns=["date", "ticker", "close"])
    return df.pivot(index="date", columns="ticker", values="close").dropna(how="all")


async def run_backtest(
    tickers: list[str],
    risk_profile: str = "modéré",
    start_date: date = None,
    end_date: date = None,
) -> dict:
    """
    Backteste la stratégie Markowitz sur une période historique.
    Rééquilibrage mensuel (rebalancing automatique via vectorbt).

    Returns:
        {
            "total_return": 0.45,
            "sharpe_ratio": 1.23,
            "max_drawdown": -0.18,
            "annual_volatility": 0.14,
            "vs_sp500": 0.12,
            "chart_data": [{"date": "...", "portfolio": 1.0, "sp500": 1.0}, ...]
        }
    """
    try:
        import vectorbt as vbt
    except ImportError:
        raise BacktestError("vectorbt non installé. Installez-le avec : pip install vectorbt")

    if start_date is None:
        start_date = date(2020, 1, 1)
    if end_date is None:
        end_date = date(2024, 12, 31)

    # Inclure SPY comme benchmark
    all_tickers = list(set(tickers + ["SPY"]))

    log.info(f"Backtest : {tickers} | {start_date} → {end_date} | profil={risk_profile}")

    # Chargement des prix
    prices = await _get_prices_for_backtest(all_tickers, start_date, end_date)

    if prices.empty:
        raise BacktestError("DataFrame de prix vide")

    # Séparer SPY
    spy_prices = prices.get("SPY", pd.Series(dtype=float))
    portfolio_tickers = [t for t in tickers if t in prices.columns]
    portfolio_prices = prices[portfolio_tickers].dropna()

    if portfolio_prices.empty:
        raise BacktestError("Pas de données pour les actifs du portefeuille")

    # ── Calcul des poids mensuels (rééquilibrage) ─────────────
    from app.services.markowitz import get_optimal_weights
    from pypfopt import EfficientFrontier, expected_returns, risk_models

    # Pour le backtest, on calcule les poids UNE FOIS sur toute la période
    # (simplification pédagogique — en production : rolling window)
    mu = expected_returns.mean_historical_return(portfolio_prices, frequency=252)
    S = risk_models.sample_cov(portfolio_prices, frequency=252)

    ef = EfficientFrontier(mu, S)
    if risk_profile == "conservateur":
        weights = ef.min_volatility()
    elif risk_profile == "agressif":
        try:
            weights = ef.efficient_return(target_return=0.25)
        except Exception:
            weights = ef.max_sharpe()
    else:
        weights = ef.max_sharpe(risk_free_rate=0.04)

    cleaned_weights = ef.clean_weights(cutoff=0.01)
    weight_series = pd.Series(cleaned_weights)

    # Filtrer les tickers disponibles
    available = [t for t in weight_series.index if t in portfolio_prices.columns]
    if not available:
        raise BacktestError("Aucun ticker commun entre les poids et les prix")

    w = weight_series[available]
    p = portfolio_prices[available].dropna()

    # ── Simulation vectorbt ───────────────────────────────────
    try:
        pf = vbt.Portfolio.from_orders(
            close=p,
            size=w.values,
            size_type="targetpercent",
            freq="1D",
            init_cash=10000,
            group_by=True,
            cash_sharing=True,
        )

        total_return = float(pf.total_return())
        sharpe = float(pf.sharpe_ratio())
        max_dd = float(pf.max_drawdown())
        annual_vol = float(pf.annualized_volatility()) if hasattr(pf, 'annualized_volatility') else float(pf.returns().std() * np.sqrt(252))

        # Benchmark SPY
        spy_return = 0.0
        if not spy_prices.empty:
            spy_filtered = spy_prices.loc[p.index[0]:p.index[-1]].dropna()
            if len(spy_filtered) > 1:
                spy_return = float(spy_filtered.iloc[-1] / spy_filtered.iloc[0] - 1)

        # Données pour le graphique frontend
        portfolio_curve = pf.value() / 10000   # Normalisé à 1.0
        spy_curve = spy_prices.loc[p.index[0]:p.index[-1]].dropna()
        spy_normalized = spy_curve / spy_curve.iloc[0] if not spy_curve.empty else pd.Series()

        chart_data = []
        for d in portfolio_curve.index:
            row = {
                "date": str(d),
                "portfolio": round(float(portfolio_curve.loc[d]), 4),
            }
            if d in spy_normalized.index:
                row["sp500"] = round(float(spy_normalized.loc[d]), 4)
            chart_data.append(row)

        return {
            "total_return": round(total_return, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd, 4),
            "annual_volatility": round(annual_vol, 4),
            "vs_sp500": round(total_return - spy_return, 4),
            "sp500_return": round(spy_return, 4),
            "weights_used": cleaned_weights,
            "tickers": available,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "chart_data": chart_data[:500],   # Max 500 points pour le frontend
        }

    except Exception as e:
        raise BacktestError(f"Erreur vectorbt : {e}") from e
