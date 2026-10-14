"""
Service Markowitz — Optimisation de portefeuille.
Bibliothèque : PyPortfolioOpt

Fonctions exportées :
  - get_optimal_weights(tickers, profile_type, lookback_days) → dict
  - get_efficient_frontier_data(tickers, lookback_days) → list[dict]
"""
import logging
from typing import Literal

import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier, expected_returns, risk_models
from pypfopt.exceptions import OptimizationError
from sqlalchemy import select, and_

from app.core.config import settings
from app.db.postgres import AsyncSessionLocal
from app.models.portfolio import PriceHistory

log = logging.getLogger(__name__)

ProfileType = Literal["conservateur", "modéré", "agressif"]


class MarkowitzError(Exception):
    pass


class InsufficientDataError(MarkowitzError):
    pass


async def _get_price_dataframe(
    tickers: list[str],
    lookback_days: int = settings.LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    Charge l'historique de prix depuis PostgreSQL.
    Retourne un DataFrame avec les tickers en colonnes et les dates en index.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PriceHistory.date, PriceHistory.ticker, PriceHistory.close)
            .where(PriceHistory.ticker.in_(tickers))
            .order_by(PriceHistory.date)
        )
        rows = result.fetchall()

    if not rows:
        raise InsufficientDataError(
            f"Aucune donnée historique disponible pour {tickers}. "
            "Lancez d'abord le chargement historique."
        )

    df = pd.DataFrame(rows, columns=["date", "ticker", "close"])
    pivot = df.pivot(index="date", columns="ticker", values="close")

    # Filtrer sur la fenêtre demandée
    pivot = pivot.tail(lookback_days).dropna(how="all")

    if len(pivot) < 60:
        raise InsufficientDataError(
            f"Données insuffisantes : {len(pivot)} jours disponibles, "
            f"minimum 60 requis pour une optimisation fiable."
        )

    # Supprimer les colonnes avec trop de NaN (> 20%)
    threshold = len(pivot) * 0.8
    pivot = pivot.dropna(axis=1, thresh=int(threshold))

    return pivot


async def get_optimal_weights(
    tickers: list[str] = None,
    profile_type: ProfileType = "modéré",
    lookback_days: int = settings.LOOKBACK_DAYS,
) -> dict:
    """
    Calcule les poids optimaux du portefeuille selon le profil de risque.

    Args:
        tickers: Liste des actifs (défaut : PRICE_TICKERS)
        profile_type: conservateur | modéré | agressif
        lookback_days: Fenêtre historique (défaut : 504 jours ≈ 2 ans)

    Returns:
        {
            "weights": {"AAPL": 0.15, "MSFT": 0.12, ...},  # somme = 1.0
            "sharpe_ratio": 1.23,
            "expected_annual_return": 0.18,
            "annual_volatility": 0.14,
            "profile_type": "modéré"
        }

    Raises:
        MarkowitzError: Si l'optimisation échoue
        InsufficientDataError: Si les données sont insuffisantes
    """
    tickers = tickers or settings.PRICE_TICKERS

    log.info(f"Optimisation Markowitz : {len(tickers)} actifs, profil={profile_type}")

    prices = await _get_price_dataframe(tickers, lookback_days)

    # Calcul des rendements attendus et matrice de covariance
    mu = expected_returns.mean_historical_return(prices, frequency=252)
    S = risk_models.sample_cov(prices, frequency=252)

    try:
        ef = EfficientFrontier(mu, S)

        if profile_type == "conservateur":
            # Minimise la volatilité — priorité à la préservation du capital
            weights = ef.min_volatility()
        elif profile_type == "modéré":
            # Maximise le ratio de Sharpe — équilibre rendement/risque
            weights = ef.max_sharpe(risk_free_rate=0.04)
        elif profile_type == "agressif":
            # Maximise le rendement pour une cible de 25% annuel
            try:
                weights = ef.efficient_return(target_return=0.25)
            except OptimizationError:
                # Fallback si 25% n'est pas atteignable
                weights = ef.max_sharpe(risk_free_rate=0.04)
                log.warning("Cible 25% non atteignable, fallback max_sharpe")
        else:
            raise MarkowitzError(f"Profil inconnu : {profile_type}")

        cleaned = ef.clean_weights(cutoff=0.01)   # Supprime les poids < 1%

        # Métriques de performance
        perf = ef.portfolio_performance(verbose=False, risk_free_rate=0.04)
        expected_return, volatility, sharpe = perf

        # Vérification : les poids doivent sommer à 1.0 (± 0.001)
        total_weight = sum(cleaned.values())
        if abs(total_weight - 1.0) > 0.001:
            raise MarkowitzError(f"Les poids ne somment pas à 1.0 : {total_weight:.6f}")

        return {
            "weights": dict(cleaned),
            "sharpe_ratio": round(float(sharpe), 4),
            "expected_annual_return": round(float(expected_return), 4),
            "annual_volatility": round(float(volatility), 4),
            "profile_type": profile_type,
            "tickers_used": list(cleaned.keys()),
        }

    except OptimizationError as e:
        raise MarkowitzError(f"Optimisation impossible : {e}") from e


async def get_efficient_frontier_data(
    tickers: list[str] = None,
    n_points: int = 50,
    lookback_days: int = settings.LOOKBACK_DAYS,
) -> list[dict]:
    """
    Génère les points de la frontière efficiente pour visualisation.
    Retourne une liste de {return, volatility, sharpe} pour le frontend.
    """
    tickers = tickers or settings.PRICE_TICKERS
    prices = await _get_price_dataframe(tickers, lookback_days)

    mu = expected_returns.mean_historical_return(prices, frequency=252)
    S = risk_models.sample_cov(prices, frequency=252)

    target_returns = np.linspace(float(mu.min()), float(mu.max()) * 0.95, n_points)
    frontier_points = []

    for target in target_returns:
        try:
            ef = EfficientFrontier(mu, S)
            ef.efficient_return(target_return=target)
            ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=0.04)
            frontier_points.append({
                "expected_return": round(float(ret), 4),
                "volatility": round(float(vol), 4),
                "sharpe_ratio": round(float(sharpe), 4),
            })
        except OptimizationError:
            continue

    return frontier_points
