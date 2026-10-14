"""
Agent Conseiller — Noeud LangGraph.
Fusionne les outputs Quant + Analyste via Mistral 7B (Groq API).
Température = 0.3 pour la cohérence financière.
"""
import json
import logging
from typing import Optional

from groq import Groq, APIError, RateLimitError

from app.core.config import settings

log = logging.getLogger(__name__)

# ── Prompt système ────────────────────────────────────────────
SYSTEM_PROMPT = """
Tu es un conseiller financier expert et fiable. 
Tu dois synthétiser des données quantitatives et qualitatives pour fournir 
une recommandation claire, personnalisée et explicable.

Règles absolues :
1. Justifie TOUJOURS chaque recommandation par des métriques concrètes.
2. Sois concis : maximum 200 mots pour l'explication.
3. Prends en compte le profil de risque de l'investisseur.
4. Signale les risques ESG si le score est < 0.4.
5. Réponds UNIQUEMENT en JSON valide selon le format demandé.
6. Réponds en français.
"""

RECOMMENDATION_FORMAT = """
Retourne UNIQUEMENT ce JSON (sans markdown, sans balises code) :
{
  "allocation": {"TICKER": 0.XX, ...},
  "explanation": "Explication en 150-200 mots...",
  "shap_summary": "Principaux facteurs : ...",
  "sentiment_summary": "Sentiment de marché : ...",
  "esg_warning": "Avertissement ESG si applicable, sinon null",
  "risk_note": "Note sur le risque global du portefeuille"
}
"""


def _build_context(state: dict) -> str:
    """Construit le contexte textuel pour le LLM à partir du state LangGraph."""
    tickers = state.get("tickers", [])
    risk_profile = state.get("risk_profile", "modéré")
    question = state.get("question", "Analyse mon portefeuille")

    # Données Quant
    weights = state.get("markowitz_weights") or {}
    sharpe = state.get("sharpe_ratio") or 0.0
    expected_return = state.get("expected_annual_return") or 0.0
    volatility = state.get("annual_volatility") or 0.0
    shap_data = state.get("shap_data") or {}
    rsi_signals = state.get("rsi_signals") or {}

    # Données Analyste
    sentiment_scores = state.get("sentiment_scores") or {}
    esg_scores = state.get("esg_scores") or {}
    graph_context = state.get("graph_context") or ""
    retrieved_news = (state.get("retrieved_news") or [])[:3]   # Max 3 news

    context = f"""
=== DEMANDE UTILISATEUR ===
Profil de risque : {risk_profile}
Question : {question}
Actifs : {', '.join(tickers)}

=== DONNÉES QUANTITATIVES (Markowitz) ===
Allocation optimale : {json.dumps(weights, indent=2)}
Ratio de Sharpe : {sharpe:.2f}
Rendement annuel attendu : {expected_return:.1%}
Volatilité annuelle : {volatility:.1%}
Facteurs SHAP : {json.dumps(shap_data.get('top_factors', [])[:3], indent=2)}
Signaux RSI : {json.dumps(rsi_signals, indent=2)}

=== ANALYSE DE MARCHÉ (FinBERT + GraphRAG) ===
Scores de sentiment : {json.dumps(sentiment_scores, indent=2)}
Scores ESG : {json.dumps(esg_scores, indent=2)}
Contexte graphe (relations) : {str(graph_context)[:500]}
Actualités pertinentes :
{chr(10).join(f"- {str(news)[:200]}" for news in retrieved_news)}

{RECOMMENDATION_FORMAT}
"""
    return context


async def run_advisor_agent(state: dict) -> dict:
    """
    Noeud LangGraph : Agent Conseiller (Mistral 7B via Groq API).

    Input state:
        - Tout le state précédent (Quant + Analyste)

    Output state:
        - recommendation: str (JSON structuré)
        - final_allocation: dict[str, float]
        - advisor_error: str | None
    """
    log.info("[AdvisorAgent] Démarrage — appel Groq API")

    context = _build_context(state)

    recommendation_json = await _call_groq_with_retry(context)

    if recommendation_json is None:
        # Fallback : recommandation basée uniquement sur Markowitz
        log.warning("[AdvisorAgent] Fallback Markowitz (Groq indisponible)")
        return _markowitz_fallback(state)

    try:
        parsed = json.loads(recommendation_json)
        final_allocation = parsed.get("allocation", state.get("markowitz_weights", {}))

        log.info("[AdvisorAgent] Recommandation générée avec succès")
        return {
            **state,
            "recommendation": recommendation_json,
            "final_allocation": final_allocation,
            "advisor_error": None,
        }

    except json.JSONDecodeError:
        log.warning("[AdvisorAgent] Réponse LLM non-parseable, fallback Markowitz")
        return _markowitz_fallback(state)


async def _call_groq_with_retry(context: str, max_retries: int = 3) -> Optional[str]:
    """
    Appel Groq API avec retry exponentiel (3 tentatives max).
    Température = 0.3 pour la cohérence financière.
    """
    import asyncio

    client = Groq(api_key=settings.GROQ_API_KEY)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            log.debug(f"[AdvisorAgent] Groq réponse: {content[:100]}...")
            return content

        except RateLimitError:
            wait = 2 ** attempt
            log.warning(f"[AdvisorAgent] Rate limit Groq, attente {wait}s (tentative {attempt+1}/{max_retries})")
            await asyncio.sleep(wait)

        except APIError as e:
            log.error(f"[AdvisorAgent] Erreur Groq API: {e}")
            if attempt == max_retries - 1:
                return None
            await asyncio.sleep(2 ** attempt)

    return None


def _markowitz_fallback(state: dict) -> dict:
    """Fallback si Groq est indisponible — utilise uniquement les données Markowitz."""
    weights = state.get("markowitz_weights") or {}
    sharpe = state.get("sharpe_ratio") or 0.0
    profile = state.get("risk_profile") or "modéré"

    fallback = {
        "allocation": weights,
        "explanation": (
            f"Recommandation basée sur l'optimisation de Markowitz (profil : {profile}). "
            f"Ratio de Sharpe obtenu : {sharpe:.2f}. "
            "L'analyse de sentiment et le graphe de connaissances sont temporairement indisponibles."
        ),
        "shap_summary": "SHAP non disponible en mode fallback.",
        "sentiment_summary": "Analyse de sentiment indisponible.",
        "esg_warning": None,
        "risk_note": f"Portefeuille optimisé pour le profil {profile}.",
    }

    return {
        **state,
        "recommendation": json.dumps(fallback, ensure_ascii=False),
        "final_allocation": weights,
        "advisor_error": "Groq API indisponible — fallback Markowitz activé",
    }
