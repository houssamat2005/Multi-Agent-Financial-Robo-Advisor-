"""
Client Neo4j (Graphe) pour gérer le graphe de connaissances.
Stocke les relations entreprises (fournisseur, concurrent, filiale) et les notes ESG.
"""
import logging
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import settings

log = logging.getLogger(__name__)

_driver: Optional[AsyncDriver] = None


async def init_neo4j() -> None:
    """Initialise le driver Neo4j."""
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URL,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        log.info(f"Connexion Neo4j initialisée sur {settings.NEO4J_URL}")


async def close_neo4j() -> None:
    """Ferme la connexion Neo4j."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


def get_neo4j_driver() -> AsyncDriver:
    """Retourne l'instance du driver (doit être initialisée)."""
    global _driver
    if _driver is None:
        raise RuntimeError("Neo4j driver non initialisé.")
    return _driver


# ── Fonctions Métier ─────────────────────────────────────────────────────────

async def run_query(query: str, parameters: dict = None) -> list[dict]:
    """Exécute une requête Cypher générique."""
    driver = get_neo4j_driver()
    async with driver.session() as session:
        result = await session.run(query, parameters or {})
        return await result.data()


async def get_company_esg(ticker: str) -> dict:
    """Récupère les scores ESG d'une entreprise."""
    query = """
    MATCH (c:Company {ticker: $ticker})
    RETURN c.esg_score AS esg_score,
           c.esg_environmental AS env,
           c.esg_social AS soc,
           c.esg_governance AS gov
    """
    driver = get_neo4j_driver()
    async with driver.session() as session:
        result = await session.run(query, ticker=ticker)
        record = await result.single()
        if record:
            return {
                "esg_score": record["esg_score"],
                "environmental": record["env"],
                "social": record["soc"],
                "governance": record["gov"],
            }
        return {}


async def get_company_competitors(ticker: str) -> list[str]:
    """Récupère la liste des tickers concurrents."""
    query = """
    MATCH (c1:Company {ticker: $ticker})-[:COMPETES_WITH]-(c2:Company)
    RETURN c2.ticker AS competitor
    """
    driver = get_neo4j_driver()
    async with driver.session() as session:
        result = await session.run(query, ticker=ticker)
        records = await result.data()
        return [r["competitor"] for r in records]
