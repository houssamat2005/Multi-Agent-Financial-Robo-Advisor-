"""
Client Redis — Singleton asynchrone.
Gère le stockage des JWT refresh tokens et le cache des prix temps réel.
"""
import json
import logging
from typing import Optional

from redis.asyncio import Redis, from_url

from app.core.config import settings

log = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialise le pool de connexion Redis."""
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(settings.REDIS_URL, decode_responses=True)
        log.info(f"Connexion Redis initialisée sur {settings.REDIS_URL}")


async def close_redis() -> None:
    """Ferme la connexion Redis proprement."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def get_redis() -> Redis:
    """Retourne l'instance Redis."""
    global _redis_client
    if _redis_client is None:
        await init_redis()
    return _redis_client


# ── Fonctions métier ──────────────────────────────────────────────────────────

async def store_refresh_token(user_id: str, token: str, expire_seconds: int = 604800) -> None:
    r = await get_redis()
    await r.set(f"refresh_token:{user_id}", token, ex=expire_seconds)


async def get_refresh_token(user_id: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(f"refresh_token:{user_id}")


async def delete_refresh_token(user_id: str) -> None:
    r = await get_redis()
    await r.delete(f"refresh_token:{user_id}")


async def set_price(ticker: str, price_data: dict, ttl: int = 300) -> None:
    """Stocke le dernier prix connu pour un ticker."""
    r = await get_redis()
    await r.set(f"price:{ticker}", json.dumps(price_data), ex=ttl)


async def get_price(ticker: str) -> Optional[dict]:
    r = await get_redis()
    data = await r.get(f"price:{ticker}")
    return json.loads(data) if data else None


async def get_all_prices(tickers: list) -> dict:
    """Récupère les prix de plusieurs tickers en un seul appel MGET."""
    r = await get_redis()
    if not tickers:
        return {}
    keys = [f"price:{t}" for t in tickers]
    values = await r.mget(*keys)
    result = {}
    for ticker, val in zip(tickers, values):
        if val:
            result[ticker] = json.loads(val)
    return result
