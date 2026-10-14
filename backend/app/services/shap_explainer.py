"""
Service SHAP — Explainability des décisions d'allocation.
Explique POURQUOI chaque actif a le poids qu'il a.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


class SHAPError(Exception):
    pass


def compute_shap_values(
    weights: dict[str, float],
    prices_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Calcule les SHAP values pour expliquer l'allocation Markowitz.

    Approche : Entraîne un Ridge Regression sur des features macro
    (volatilité, momentum, volume moyen) → poids Markowitz,
    puis SHAP explique la contribution de chaque feature.

    Returns:
        {
            "top_factors": [
                {"factor": "volatilité_AAPL", "contribution": 0.032, "direction": "positive"},
                ...
            ],
            "summary": "L'allocation est principalement expliquée par..."
        }
    """
    if not weights:
        return {"top_factors": [], "summary": "Aucune allocation disponible."}

    try:
        import shap
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler

        if prices_df is None or prices_df.empty:
            # Mode dégradé : retourne les poids directs comme facteurs
            return _fallback_shap(weights)

        tickers = list(weights.keys())
        ticker_prices = prices_df[tickers].dropna() if all(t in prices_df.columns for t in tickers) else prices_df.dropna()

        # Construire les features : rendement moyen, volatilité, momentum 30j
        features = {}
        for ticker in tickers:
            if ticker not in ticker_prices.columns:
                continue
            series = ticker_prices[ticker].dropna()
            returns = series.pct_change().dropna()

            features[f"volatilite_{ticker}"] = returns.std() * np.sqrt(252)
            features[f"momentum_{ticker}"] = (series.iloc[-1] / series.iloc[-30] - 1) if len(series) >= 30 else 0.0
            features[f"rendement_{ticker}"] = returns.mean() * 252

        X = np.array(list(features.values())).reshape(1, -1)
        y = np.array([weights.get(t, 0) for t in tickers if t in ticker_prices.columns])

        if len(y) == 0 or X.shape[1] == 0:
            return _fallback_shap(weights)

        # Entraîner Ridge sur un échantillon bootstrap
        n_bootstrap = min(100, len(ticker_prices))
        X_train = []
        y_train = []

        for _ in range(n_bootstrap):
            noise = np.random.normal(0, 0.001, X.shape)
            X_train.append((X + noise)[0])
            y_train.append(y[0] if len(y) > 0 else 0)

        X_train = np.array(X_train)
        y_train = np.array(y_train)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_train)

        model = Ridge(alpha=1.0)
        model.fit(X_scaled, y_train)

        # SHAP TreeExplainer / LinearExplainer
        explainer = shap.LinearExplainer(model, X_scaled)
        shap_values = explainer.shap_values(scaler.transform(X))

        # Top 5 facteurs par contribution absolue
        feature_names = list(features.keys())
        shap_array = shap_values[0] if shap_values.ndim > 1 else shap_values

        top_indices = np.argsort(np.abs(shap_array))[::-1][:5]
        top_factors = []

        for idx in top_indices:
            if idx < len(feature_names):
                contribution = float(shap_array[idx])
                top_factors.append({
                    "factor": feature_names[idx],
                    "contribution": round(contribution, 4),
                    "direction": "positive" if contribution > 0 else "negative",
                })

        summary = _build_summary(top_factors)

        return {
            "top_factors": top_factors,
            "summary": summary,
            "method": "shap_linear",
        }

    except Exception as e:
        log.warning(f"SHAP computation failed, using fallback: {e}")
        return _fallback_shap(weights)


def _fallback_shap(weights: dict[str, float]) -> dict:
    """SHAP simplifié : retourne les poids comme proxy de contribution."""
    sorted_weights = sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True)
    top_factors = [
        {
            "factor": f"allocation_{ticker}",
            "contribution": round(weight, 4),
            "direction": "positive" if weight > 0 else "negative",
        }
        for ticker, weight in sorted_weights[:5]
    ]
    return {
        "top_factors": top_factors,
        "summary": "Allocation basée sur l'optimisation Markowitz (ratio de Sharpe).",
        "method": "fallback",
    }


def _build_summary(top_factors: list[dict]) -> str:
    """Génère une description textuelle des principaux facteurs SHAP."""
    if not top_factors:
        return "Analyse SHAP non disponible."

    positive = [f for f in top_factors if f["direction"] == "positive"]
    negative = [f for f in top_factors if f["direction"] == "negative"]

    parts = []
    if positive:
        parts.append(f"Favorisé par : {', '.join(f['factor'] for f in positive[:2])}")
    if negative:
        parts.append(f"Pénalisé par : {', '.join(f['factor'] for f in negative[:2])}")

    return ". ".join(parts) + "."
