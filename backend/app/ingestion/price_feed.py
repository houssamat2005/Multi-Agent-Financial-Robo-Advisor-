"""
Producteur de flux de prix (Mock) → Kafka.
Simule un flux WebSocket en interrogeant yfinance à intervalles réguliers
et envoie les données dans le topic Kafka 'prices-raw'.
"""
import asyncio
import json
import logging
import traceback
from datetime import datetime, timezone
import yfinance as yf
from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.db.redis_client import set_price

log = logging.getLogger(__name__)

KAFKA_TOPIC = "prices-raw"


async def fetch_prices_and_produce(producer: AIOKafkaProducer):
    """Récupère les prix et les envoie dans Kafka."""
    tickers = settings.PRICE_TICKERS
    try:
        data = yf.download(tickers, period="1d", interval="1m", progress=False)
        if data.empty:
            return

        for ticker in tickers:
            try:
                if "Close" in data and ticker in data["Close"]:
                    close_price = data["Close"][ticker].dropna()
                    if not close_price.empty:
                        last_price = float(close_price.iloc[-1])
                        
                        message = {
                            "ticker": ticker,
                            "price": last_price,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # 1. Envoi à Kafka
                        await producer.send_and_wait(
                            topic=KAFKA_TOPIC,
                            key=ticker.encode("utf-8"),
                            value=json.dumps(message).encode("utf-8")
                        )
                        
                        # 2. Cache Redis immédiat
                        await set_price(ticker, message)
                        
            except Exception as e:
                log.error(f"Erreur price feed {ticker}: {e}")
                
    except Exception as e:
        log.error(f"Erreur price feed global: {e}\n{traceback.format_exc()}")


async def start_price_feed():
    """Démarre la boucle de production de prix."""
    log.info(f"Démarrage du flux de prix vers Kafka ({settings.KAFKA_BOOTSTRAP_SERVERS})...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        client_id="price-producer"
    )
    
    await producer.start()
    try:
        while True:
            await fetch_prices_and_produce(producer)
            await asyncio.sleep(settings.PRICE_POLL_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        log.info("Arrêt du flux de prix.")
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(start_price_feed())
