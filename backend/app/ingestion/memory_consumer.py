"""
Consommateur en mémoire (remplace Kafka).
Écoute les queues prices_queue et news_queue en parallèle.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db.redis_client import set_price
from app.core.queues import prices_queue, news_queue

log = logging.getLogger(__name__)

async def consume_prices() -> None:
    """Consomme la queue de prix et met à jour le cache mémoire."""
    log.info("Memory consumer [prices] démarré")
    try:
        while True:
            data = await prices_queue.get()
            try:
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
                log.debug(f"Prix mis à jour en mémoire : {ticker} = {price_data['close']}")
            except Exception as e:
                log.error(f"Erreur traitement prix: {e}")
            finally:
                prices_queue.task_done()
    except asyncio.CancelledError:
        pass


async def consume_news() -> None:
    """Consomme la queue de news et lance FinBERT/ChromaDB."""
    from app.services.finbert import analyze_sentiment
    from app.db.chroma_client import add_documents, COLLECTION_FINANCIAL_NEWS

    log.info("Memory consumer [news] démarré")
    try:
        while True:
            data = await news_queue.get()
            try:
                title = data.get("title", "")
                content = data.get("content", "")
                tickers = data.get("tickers", [])
                source = data.get("source", "unknown")
                published_at = data.get("published_at", datetime.now(timezone.utc).isoformat())

                text = f"{title}. {content}"[:512]

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
                log.error(f"Erreur traitement news: {e}")
            finally:
                news_queue.task_done()
    except asyncio.CancelledError:
        pass


async def start_all_consumers() -> None:
    """Lance tous les consumers en parallèle."""
    await asyncio.gather(
        consume_prices(),
        consume_news(),
    )
