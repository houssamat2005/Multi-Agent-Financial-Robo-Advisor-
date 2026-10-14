"""
Script d'initialisation du graphe de connaissances Neo4j.
Peuple la base avec des entreprises et des relations simulées/statiques.
"""
import asyncio
import logging

from app.core.config import settings
from app.db.neo4j_client import get_neo4j, run_query

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# Données statiques de base pour le MVP
COMPANIES = [
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "country": "USA", "esg_score": 75.5},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "country": "USA", "esg_score": 88.2},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "country": "USA", "esg_score": 81.0},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "country": "USA", "esg_score": 62.4},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology", "country": "USA", "esg_score": 85.1},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Cyclical", "country": "USA", "esg_score": 58.9},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "country": "USA", "esg_score": 60.5},
    {"ticker": "BRK-B", "name": "Berkshire Hathaway", "sector": "Financials", "country": "USA", "esg_score": 45.0},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials", "country": "USA", "esg_score": 65.2},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Financials", "country": "USA", "esg_score": 78.4},
]

RELATIONS = [
    # Concurrents
    ("AAPL", "COMPETES_WITH", "MSFT"),
    ("AAPL", "COMPETES_WITH", "GOOGL"),
    ("MSFT", "COMPETES_WITH", "GOOGL"),
    ("MSFT", "COMPETES_WITH", "AMZN"),
    # Fournisseurs
    ("NVDA", "SUPPLIES", "MSFT"),
    ("NVDA", "SUPPLIES", "GOOGL"),
    ("NVDA", "SUPPLIES", "AMZN"),
    ("NVDA", "SUPPLIES", "META"),
    ("NVDA", "SUPPLIES", "TSLA"),
    # Partenariats / Autres
    ("JPM", "PARTNERS_WITH", "V"),
    ("BRK-B", "INVESTS_IN", "AAPL"),
]


async def init_neo4j():
    """Initialise le graphe Neo4j avec les contraintes et les données de base."""
    log.info("Connexion à Neo4j...")
    
    try:
        # Créer les contraintes
        log.info("Création des contraintes et index...")
        await run_query("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE")
        await run_query("CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)")
        
        # Insérer les entreprises
        log.info("Insertion des entreprises...")
        for c in COMPANIES:
            cypher = """
            MERGE (comp:Company {ticker: $ticker})
            SET comp.name = $name,
                comp.sector = $sector,
                comp.country = $country,
                comp.esg_score = $esg_score
            """
            await run_query(cypher, c)
            
        # Insérer les relations
        log.info("Insertion des relations...")
        for source, rel_type, target in RELATIONS:
            cypher = f"""
            MATCH (s:Company {{ticker: $source}})
            MATCH (t:Company {{ticker: $target}})
            MERGE (s)-[:{rel_type}]->(t)
            """
            await run_query(cypher, {"source": source, "target": target})
            
        log.info("Initialisation de Neo4j terminée avec succès !")
        
    except Exception as e:
        log.error(f"Erreur lors de l'initialisation de Neo4j: {e}")
        
    finally:
        from app.db.neo4j_client import close_neo4j
        await close_neo4j()


if __name__ == "__main__":
    asyncio.run(init_neo4j())
