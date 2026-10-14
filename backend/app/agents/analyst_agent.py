"""
Agent Analyste — Noeud LangGraph.
Combine : GraphRAG (Neo4j + ChromaDB) + FinBERT + ESG scoring.
"""
import asyncio
import logging

from app.services.graph_rag import get_graph_context, retrieve_relevant_news, compute_esg_weight
from app.services.finbert import analyze_sentiment, sentiment_to_score

log = logging.getLogger(__name__)


async def run_analyst_agent(state: dict) -> dict:
    """
    Noeud LangGraph : Agent Analyste de Marché.

    Input state:
        - tickers: list[str]
        - question: str (question de l'utilisateur)

    Output state (merge):
        - sentiment_scores: dict[str, float]  # -1 à +1
        - esg_scores: dict[str, float]        # 0 à 1
        - graph_context: str                   # Relations Neo4j
        - retrieved_news: list[str]            # Passages ChromaDB
        - analyst_error: str | None
    """
    tickers = state.get("tickers", [])
    question = state.get("question", "")

    log.info(f"[AnalystAgent] Démarrage — {len(tickers)} actifs")

    try:
        # ── Exécution parallèle de toutes les analyses ──────
        graph_context_task = get_graph_context(tickers)
        news_task = retrieve_relevant_news(tickers, query=question, n_results=5)
        esg_tasks = [compute_esg_weight(ticker) for ticker in tickers]

        # Gather toutes les tâches async
        results = await asyncio.gather(
            graph_context_task,
            news_task,
            *esg_tasks,
            return_exceptions=True,
        )

        graph_context = results[0] if not isinstance(results[0], Exception) else ""
        retrieved_news = results[1] if not isinstance(results[1], Exception) else []
        esg_raw = results[2:]  # Un score par ticker

        # ── ESG scores ───────────────────────────────────────
        esg_scores = {}
        for i, ticker in enumerate(tickers):
            if i < len(esg_raw) and not isinstance(esg_raw[i], Exception):
                esg_scores[ticker] = float(esg_raw[i])
            else:
                esg_scores[ticker] = 0.5   # Neutre par défaut

        # ── Analyse de sentiment sur les news récupérées ─────
        sentiment_scores = {}
        if retrieved_news:
            # Analyse batch sur les 5 premières news
            news_texts = [n.split("] ", 1)[-1] for n in retrieved_news[:5]]

            loop = asyncio.get_event_loop()
            sentiments = await loop.run_in_executor(
                None,
                _batch_analyze,
                news_texts,
            )

            # Agrège par ticker mentionné
            for ticker in tickers:
                ticker_sentiments = [
                    sentiment_to_score(s)
                    for news, s in zip(retrieved_news[:5], sentiments)
                    if ticker in news
                ]
                if ticker_sentiments:
                    sentiment_scores[ticker] = round(sum(ticker_sentiments) / len(ticker_sentiments), 3)
                else:
                    sentiment_scores[ticker] = 0.0   # Neutre si pas de news

        log.info(f"[AnalystAgent] OK — {len(retrieved_news)} news, {len(esg_scores)} ESG scores")

        return {
            **state,
            "sentiment_scores": sentiment_scores,
            "esg_scores": esg_scores,
            "graph_context": graph_context or "Aucune relation détectée dans le graphe.",
            "retrieved_news": retrieved_news,
            "analyst_error": None,
        }

    except Exception as e:
        log.error(f"[AnalystAgent] Erreur: {e}")
        return {
            **state,
            "sentiment_scores": {},
            "esg_scores": {},
            "graph_context": "",
            "retrieved_news": [],
            "analyst_error": str(e),
        }


def _batch_analyze(texts: list[str]) -> list[dict]:
    """Wrapper synchrone pour l'analyse batch FinBERT."""
    from app.services.finbert import batch_analyze_sentiment
    return batch_analyze_sentiment(texts)
