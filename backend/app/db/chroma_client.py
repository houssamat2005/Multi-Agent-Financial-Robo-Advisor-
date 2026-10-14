"""
Client ChromaDB singleton (HTTP vers le conteneur Docker).
Utilisé pour le stockage vectoriel des news et rapports ESG (RAG).
"""
import logging
from typing import Optional

import chromadb
from chromadb import AsyncHttpClient

from app.core.config import settings

log = logging.getLogger(__name__)

_chroma_client: Optional[AsyncHttpClient] = None

COLLECTION_FINANCIAL_NEWS = "financial_news"
COLLECTION_ESG_REPORTS = "esg_reports"


async def get_chroma() -> AsyncHttpClient:
    """Retourne le client ChromaDB (singleton)."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = await chromadb.AsyncHttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        log.info(f"ChromaDB connecté sur {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
    return _chroma_client


async def close_chroma() -> None:
    """Réinitialise le client ChromaDB."""
    global _chroma_client
    _chroma_client = None


async def get_or_create_collection(name: str, metadata: dict = None):
    """Récupère ou crée une collection ChromaDB."""
    client = await get_chroma()
    return await client.get_or_create_collection(
        name=name,
        metadata=metadata or {"hnsw:space": "cosine"},
    )


async def add_documents(
    collection_name: str,
    documents: list,
    metadatas: list,
    ids: list,
) -> None:
    """Ajoute des documents vectorisés dans une collection."""
    try:
        collection = await get_or_create_collection(collection_name)
        await collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
    except Exception as e:
        log.warning(f"ChromaDB add_documents: {e}")


async def query_collection(
    collection_name: str,
    query_texts: list,
    n_results: int = 5,
    where: dict = None,
) -> dict:
    """
    Recherche sémantique dans une collection ChromaDB.
    Retourne : {"documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
    """
    try:
        collection = await get_or_create_collection(collection_name)
        kwargs = {
            "query_texts": query_texts,
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return await collection.query(**kwargs)
    except Exception as e:
        log.warning(f"ChromaDB query: {e}")
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
