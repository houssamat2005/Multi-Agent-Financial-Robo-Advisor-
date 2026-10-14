"""
Routes marché — WebSocket pour les prix en temps réel.
GET /market/prices/ws/{portfolio_id}
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.db.redis_client import get_redis
from app.models.portfolio import Holding

router = APIRouter()
log = logging.getLogger(__name__)


@router.websocket("/prices/ws/{portfolio_id}")
async def websocket_prices_endpoint(
    websocket: WebSocket,
    portfolio_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Connexion WebSocket pour recevoir les prix live d'un portefeuille.
    Le client se connecte, et le serveur lui envoie les prix depuis Redis en polling rapide.
    """
    await websocket.accept()
    log.info(f"WebSocket client connected for portfolio: {portfolio_id}")

    try:
        # Récupérer les tickers du portefeuille
        result = await db.execute(select(Holding.ticker).where(Holding.portfolio_id == portfolio_id))
        tickers = result.scalars().all()
        
        if not tickers:
            await websocket.send_json({"error": "Portfolio is empty or not found"})
            await websocket.close()
            return
            
        r = await get_redis()
        
        while True:
            # Récupérer tous les prix live
            keys = [f"price:{t}" for t in tickers]
            values = await r.mget(*keys)
            
            prices_data = {}
            for ticker, v in zip(tickers, values):
                if v:
                    prices_data[ticker] = json.loads(v)
                    
            await websocket.send_json({"type": "prices_update", "data": prices_data})
            
            # Polling delay (e.g. update every 2 seconds)
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        log.info(f"WebSocket client disconnected for portfolio: {portfolio_id}")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
