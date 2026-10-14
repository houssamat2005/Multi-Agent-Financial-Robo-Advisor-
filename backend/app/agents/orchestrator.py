"""
Orchestrateur LangGraph — Graph multi-agents.
Architecture : Quant + Analyste (parallèle) → Conseiller → Output

Monitoring : LangSmith (LANGCHAIN_TRACING_V2=true)
"""
import json
import logging
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, START, END

from app.agents.quant_agent import run_quant_agent
from app.agents.analyst_agent import run_analyst_agent
from app.agents.advisor_agent import run_advisor_agent

log = logging.getLogger(__name__)


# ── État partagé entre tous les agents ───────────────────────
class AdvisorState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────
    user_id: str
    portfolio_id: str
    question: str
    risk_profile: str           # conservateur | modéré | agressif
    tickers: list[str]

    # ── Résultats Agent Quantitatif ───────────────────────────
    markowitz_weights: dict[str, float]
    sharpe_ratio: float
    expected_annual_return: float
    annual_volatility: float
    rsi_signals: dict[str, Any]
    shap_data: dict
    quant_error: Optional[str]

    # ── Résultats Agent Analyste ──────────────────────────────
    sentiment_scores: dict[str, float]
    esg_scores: dict[str, float]
    graph_context: str
    retrieved_news: list[str]
    analyst_error: Optional[str]

    # ── Résultats Agent Conseiller ────────────────────────────
    recommendation: str
    final_allocation: dict[str, float]
    advisor_error: Optional[str]


def format_final_output(state: AdvisorState) -> AdvisorState:
    """
    Noeud final : valide et structure la réponse complète.
    Garantit que la réponse est toujours complète même en cas d'erreur partielle.
    """
    errors = {
        k: v for k, v in {
            "quant": state.get("quant_error"),
            "analyst": state.get("analyst_error"),
            "advisor": state.get("advisor_error"),
        }.items() if v
    }

    if errors:
        log.warning(f"[Orchestrator] Erreurs partielles: {errors}")

    # S'assurer qu'une recommandation est toujours présente
    if not state.get("recommendation"):
        fallback = {
            "allocation": state.get("markowitz_weights", {}),
            "explanation": "Recommandation partielle — certains services sont indisponibles.",
            "shap_summary": "",
            "sentiment_summary": "",
            "esg_warning": None,
            "risk_note": "Vérifiez la disponibilité des services.",
        }
        state["recommendation"] = json.dumps(fallback, ensure_ascii=False)
        state["final_allocation"] = state.get("markowitz_weights", {})

    log.info("[Orchestrator] Output formaté avec succès")
    return state


def build_graph() -> Any:
    """
    Construit et compile le graphe LangGraph.

    Structure :
        START → [quant_agent, analyst_agent] (parallèle)
              → advisor_agent
              → format_output
              → END
    """
    graph = StateGraph(AdvisorState)

    # Ajouter les noeuds
    graph.add_node("quant_agent", run_quant_agent)
    graph.add_node("analyst_agent", run_analyst_agent)
    graph.add_node("advisor_agent", run_advisor_agent)
    graph.add_node("format_output", format_final_output)

    # ── Edges : exécution séquentielle ──────────
    graph.add_edge(START, "quant_agent")
    graph.add_edge("quant_agent", "analyst_agent")
    graph.add_edge("analyst_agent", "advisor_agent")
    graph.add_edge("advisor_agent", "format_output")
    graph.add_edge("format_output", END)

    return graph.compile()


# ── Instance compilée (singleton) ────────────────────────────
_graph = None


def get_graph():
    """Retourne l'instance compilée du graphe (singleton)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
        log.info("[Orchestrator] Graphe LangGraph compilé")
    return _graph


async def run_recommendation(
    user_id: str,
    portfolio_id: str,
    risk_profile: str,
    tickers: list[str],
    question: str = "Analyse mon portefeuille et donne-moi des recommandations.",
) -> AdvisorState:
    """
    Point d'entrée principal : lance le graphe complet et retourne le résultat.

    Args:
        user_id: ID de l'utilisateur
        portfolio_id: ID du portefeuille
        risk_profile: conservateur | modéré | agressif
        tickers: Liste des actifs du portefeuille
        question: Question de l'utilisateur

    Returns:
        AdvisorState complet avec recommendation, final_allocation, etc.

    Raises:
        Exception si le graphe plante complètement (normalement impossible car
        chaque agent a son propre try/except)
    """
    initial_state: AdvisorState = {
        "user_id": user_id,
        "portfolio_id": portfolio_id,
        "question": question,
        "risk_profile": risk_profile,
        "tickers": tickers,
    }

    log.info(
        f"[Orchestrator] Lancement — user={user_id}, portfolio={portfolio_id}, "
        f"profile={risk_profile}, {len(tickers)} actifs"
    )

    graph = get_graph()
    final_state = await graph.ainvoke(initial_state)

    log.info(f"[Orchestrator] Terminé — erreurs: quant={final_state.get('quant_error')}, "
             f"analyst={final_state.get('analyst_error')}, advisor={final_state.get('advisor_error')}")

    return final_state
