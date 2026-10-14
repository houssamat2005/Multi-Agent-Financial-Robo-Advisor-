"""
Producteur de flux de news → Kafka.
Récupère les articles via NewsAPI et les publie dans 'news-raw'.
"""
import asyncio
import json
import logging
import traceback
from datetime import datetime, timezone
import aiohttp
from aiokafka import AIOKafkaProducer

from app.core.config import settings

log = logging.getLogger(__name__)

KAFKA_TOPIC = "news-raw"


async def fetch_news_and_produce(producer: AIOKafkaProducer):
    """Récupère les news et les publie dans Kafka."""
    if not settings.NEWS_API_KEY:
        log.warning("Pas de NEWS_API_KEY configurée, ingestion news désactivée.")
        return

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "category": "business",
        "language": "en",
        "apiKey": settings.NEWS_API_KEY,
        "pageSize": 10
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    log.error(f"NewsAPI erreur HTTP: {resp.status}")
                    return
                data = await resp.json()

        articles = data.get("articles", [])
        for article in articles:
            if not article.get("title"):
                continue

            message = {
                "title": article["title"],
                "content": article.get("description", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": article.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                "url": article.get("url", "")
            }

            await producer.send_and_wait(
                topic=KAFKA_TOPIC,
                key=message["source"].encode("utf-8"),
                value=json.dumps(message).encode("utf-8")
            )
            
    except Exception as e:
        log.error(f"Erreur news feed: {e}\n{traceback.format_exc()}")


async def start_news_feed():
    """Démarre la boucle de production de news."""
    log.info(f"Démarrage du flux de news vers Kafka...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        client_id="news-producer"
    )
    
    await producer.start()
    try:
        while True:
            await fetch_news_and_produce(producer)
            await asyncio.sleep(settings.NEWS_POLL_INTERVAL_MINUTES * 60)
    except asyncio.CancelledError:
        log.info("Arrêt du flux de news.")
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(start_news_feed())
