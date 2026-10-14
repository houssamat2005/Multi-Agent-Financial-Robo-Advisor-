"""
Service GraphRAG — Graphe de connaissances + RAG sur news vectorisées.
Combine Neo4j (contexte graphe) + ChromaDB (news pertinentes).
"""
import logging
from datetime import datetime, timedelta, timezone

from app.db.neo4j_client import run_query
from app.db.chroma_client import query_collection, COLLECTION_FINANCIAL_NEWS

log = logging.getLogger(__name__)


class GraphRAGError(Exception):
    pass


async def get_graph_context(tickers: list[str], depth: int = 2) -> str:
    """
    Interroge Neo4j pour trouver les relations entre les entreprises (jusqu'à 2 sauts).

    Args:
        tickers: Liste de tickers boursiers
        depth: Profondeur de recherche dans le graphe (défaut 2 sauts)

    Returns:
        Description textuelle des relations trouvées.
        Ex: "AAPL → SUPPLIES → TSLA | MSFT → COMPETES_WITH → GOOGL"
    """
    if not tickers:
        return ""

    relations_text = []

    for ticker in tickers:
        try:
            # Requête multi-sauts : fournisseurs, concurrents, partenaires
            cypher = f"""
            MATCH (c:Company {{ticker: $ticker}})-[r:SUPPLIES|COMPETES_WITH|PRODUCES*1..{depth}]-(related)
            RETURN 
                c.ticker AS source,
                c.name AS source_name,
                type(r) AS relation_type,
                related.ticker AS target,
                related.name AS target_name,
                related.esg_score AS esg_score
            LIMIT 10
            """
            results = await run_query(cypher, {"ticker": ticker})

            for row in results:
                source = row.get("source", ticker)
                relation = row.get("relation_type", "RELATED_TO")
                target = row.get("target", "")
                target_name = row.get("target_name", "")
                esg = row.get("esg_score")

                if target:
                    rel_str = f"{source} →[{relation}]→ {target}"
                    if target_name:
                        rel_str += f" ({target_name})"
                    if esg is not None:
                        rel_str += f" [ESG: {esg:.1f}]"
                    relations_text.append(rel_str)

        except Exception as e:
            log.warning(f"Neo4j query failed for {ticker}: {e}")

    if not relations_text:
        return f"Aucune relation trouvée dans le graphe pour : {', '.join(tickers)}"

    return " | ".join(relations_text)


async def retrieve_relevant_news(
    tickers: list[str],
    query: str = "",
    n_results: int = 5,
    days_back: int = 30,
) -> list[str]:
    """
    Recherche sémantique dans ChromaDB pour les news pertinentes.

    Args:
        tickers: Tickers sur lesquels filtrer
        query: Requête textuelle pour la recherche sémantique
        n_results: Nombre de résultats à retourner
        days_back: Fenêtre temporelle (défaut : 30 derniers jours)

    Returns:
        Liste de passages textuels pertinents
    """
    if not tickers and not query:
        return []

    # Construction de la requête sémantique
    query_text = query or f"financial news about {' and '.join(tickers)}"

    # Filtre temporel
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    try:
        results = await query_collection(
            collection_name=COLLECTION_FINANCIAL_NEWS,
            query_texts=[query_text],
            n_results=n_results,
            where={"published_at": {"$gte": cutoff_date}} if days_back else None,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        passages = []
        for doc, meta in zip(documents, metadatas):
            source = meta.get("source", "inconnu")
            sentiment = meta.get("sentiment_label", "neutral")
            date = meta.get("published_at", "")[:10]
            passages.append(f"[{source} | {date} | {sentiment}] {doc}")

        return passages

    except Exception as e:
        log.warning(f"ChromaDB query failed: {e}")
        return []


async def compute_esg_weight(ticker: str) -> float:
    """
    Récupère le score ESG normalisé d'une entreprise depuis Neo4j.

    Returns:
        Score normalisé entre 0.0 (très mauvais) et 1.0 (excellent)
        Retourne 0.5 si le score n'est pas disponible.
    """
    try:
        results = await run_query(
            "MATCH (c:Company {ticker: $ticker}) RETURN c.esg_score AS esg_score",
            {"ticker": ticker},
        )

        if results and results[0].get("esg_score") is not None:
            raw_score = float(results[0]["esg_score"])
            # Normaliser entre 0 et 1 (hypothèse : scores ESG entre 0 et 100)
            return min(max(raw_score / 100.0, 0.0), 1.0)

    except Exception as e:
        log.warning(f"ESG score query failed for {ticker}: {e}")

    return 0.5   # Valeur neutre par défaut
