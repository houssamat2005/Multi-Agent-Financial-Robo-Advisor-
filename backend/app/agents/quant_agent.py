"""
Agent Quantitatif — Noeud LangGraph.
Calcule : Markowitz weights, RSI, SHAP values.
Aucun appel LLM dans cet agent — Python numérique pur.
"""
import logging

import pandas as pd

from app.services.markowitz import get_optimal_weights, InsufficientDataError, MarkowitzError
from app.services.shap_explainer import compute_shap_values

log = logging.getLogger(__name__)


async def run_quant_agent(state: dict) -> dict:
    """
    Noeud LangGraph : Agent Quantitatif.

    Input state:
        - user_id, portfolio_id, question
        - risk_profile: "conservateur" | "modéré" | "agressif"
        - tickers: list[str]

    Output state (merge):
        - markowitz_weights: dict[str, float]
        - sharpe_ratio: float
        - expected_annual_return: float
        - annual_volatility: float
        - shap_data: dict
        - quant_error: str | None
    """
    tickers = state.get("tickers", [])
    risk_profile = state.get("risk_profile", "modéré")

    log.info(f"[QuantAgent] Démarrage — {len(tickers)} actifs, profil={risk_profile}")

    try:
        # ── Optimisation Markowitz ──────────────────────────
        markowitz_result = await get_optimal_weights(
            tickers=tickers if tickers else None,
            profile_type=risk_profile,
        )

        weights = markowitz_result["weights"]
        sharpe = markowitz_result["sharpe_ratio"]
        expected_return = markowitz_result["expected_annual_return"]
        volatility = markowitz_result["annual_volatility"]

        log.info(f"[QuantAgent] Markowitz OK — Sharpe={sharpe:.2f}, Vol={volatility:.2%}")

        # ── RSI et signaux techniques ───────────────────────
        rsi_signals = await _compute_rsi_signals(list(weights.keys()))

        # ── SHAP values ─────────────────────────────────────
        shap_data = compute_shap_values(weights)

        return {
            **state,
            "markowitz_weights": weights,
            "sharpe_ratio": sharpe,
            "expected_annual_return": expected_return,
            "annual_volatility": volatility,
            "rsi_signals": rsi_signals,
            "shap_data": shap_data,
            "quant_error": None,
        }

    except InsufficientDataError as e:
        log.warning(f"[QuantAgent] Données insuffisantes: {e}")
        return {**state, "quant_error": str(e), "markowitz_weights": {}, "shap_data": {}}

    except MarkowitzError as e:
        log.error(f"[QuantAgent] Erreur Markowitz: {e}")
        return {**state, "quant_error": str(e), "markowitz_weights": {}, "shap_data": {}}


async def _compute_rsi_signals(tickers: list[str], window: int = 14) -> dict[str, dict]:
    """
    Calcule le RSI pour chaque ticker et retourne le signal.
    RSI > 70 → suracheté (sell signal)
    RSI < 30 → survendu (buy signal)
    30–70    → neutre (hold)
    """
    from app.db.postgres import AsyncSessionLocal
    from app.models.portfolio import PriceHistory
    from sqlalchemy import select
    import ta

    signals = {}

    async with AsyncSessionLocal() as db:
        for ticker in tickers[:10]:   # Limite pour éviter trop de requêtes
            try:
                result = await db.execute(
                    select(PriceHistory.close)
                    .where(PriceHistory.ticker == ticker)
                    .order_by(PriceHistory.date.desc())
                    .limit(60)
                )
                prices = [row[0] for row in result.fetchall()]

                if len(prices) < window + 1:
                    signals[ticker] = {"rsi": 50.0, "signal": "hold"}
                    continue

                prices_series = pd.Series(list(reversed(prices)))
                rsi_series = ta.momentum.rsi(prices_series, window=window)
                rsi_value = float(rsi_series.iloc[-1])

                signal = "sell" if rsi_value > 70 else "buy" if rsi_value < 30 else "hold"
                signals[ticker] = {"rsi": round(rsi_value, 2), "signal": signal}

            except Exception as e:
                log.warning(f"RSI failed for {ticker}: {e}")
                signals[ticker] = {"rsi": 50.0, "signal": "hold"}

    return signals
