"""
Consommateur Kafka.
Écoute les topics prices-raw et news-raw en parallèle.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.db.redis_client import set_price

log = logging.getLogger(__name__)


async def consume_prices() -> None:
    """
    Consomme le topic 'prices-raw' :
    - Met à jour Redis (cache live)
    """
    consumer = AIOKafkaConsumer(
        "prices-raw",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="price-consumer-group",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    await consumer.start()
    log.info("Kafka consumer [prices-raw] démarré")

    try:
        async for msg in consumer:
            try:
                data = msg.value
                ticker = data.get("ticker")
                if not ticker:
                    continue

                price_data = {
                    "close": data.get("price"),
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "volume": data.get("volume"),
                    "timestamp": data.get("timestamp"),
                }
                await set_price(ticker, price_data, ttl=300)
                log.debug(f"Prix mis à jour : {ticker} = {price_data['close']}")

            except Exception as e:
                log.error(f"Erreur traitement prix Kafka: {e}")

    finally:
        await consumer.stop()


async def consume_news() -> None:
    """
    Consomme le topic 'news-raw' :
    - Lance le pipeline FinBERT + vectorisation + Neo4j
    """
    from app.services.finbert import analyze_sentiment
    from app.db.chroma_client import add_documents, COLLECTION_FINANCIAL_NEWS

    consumer = AIOKafkaConsumer(
        "news-raw",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="news-consumer-group",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    await consumer.start()
    log.info("Kafka consumer [news-raw] démarré")

    try:
        async for msg in consumer:
            try:
                data = msg.value
                title = data.get("title", "")
                content = data.get("content", "")
                tickers = data.get("tickers", [])
                source = data.get("source", "unknown")
                published_at = data.get("published_at", datetime.now(timezone.utc).isoformat())

                text = f"{title}. {content}"[:512]   # Limite FinBERT

                # Analyse de sentiment FinBERT
                sentiment = await asyncio.get_event_loop().run_in_executor(
                    None, analyze_sentiment, text
                )

                # Vectorisation et stockage ChromaDB
                doc_id = f"{source}_{published_at}_{hash(text) % 10**8}"
                await add_documents(
                    collection_name=COLLECTION_FINANCIAL_NEWS,
                    documents=[text],
                    metadatas=[{
                        "ticker": ",".join(tickers),
                        "source": source,
                        "published_at": published_at,
                        "sentiment_label": sentiment["label"],
                        "sentiment_score": str(sentiment["score"]),
                    }],
                    ids=[doc_id],
                )

                log.info(f"News ingérée: {title[:50]}... | sentiment={sentiment['label']}")

            except Exception as e:
                log.error(f"Erreur traitement news Kafka: {e}")

    finally:
        await consumer.stop()


async def start_all_consumers() -> None:
    """Lance tous les consumers en parallèle."""
    await asyncio.gather(
        consume_prices(),
        consume_news(),
    )
