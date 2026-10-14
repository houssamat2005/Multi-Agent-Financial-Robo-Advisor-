"""
Tâche Celery de rééquilibrage automatique.
Vérifie la dérive (drift) des portefeuilles et crée des alertes si nécessaire.
"""
import asyncio
import logging
from celery import shared_task

from app.core.config import settings
from app.db.postgres import AsyncSessionLocal
from app.models.portfolio import Portfolio, Holding, Alert
from app.db.redis_client import get_all_prices
from sqlalchemy import select

log = logging.getLogger(__name__)


async def _check_drift_async():
    """
    Logique asynchrone pour vérifier la dérive de tous les portefeuilles.
    """
    async with AsyncSessionLocal() as db:
        # Récupérer tous les portefeuilles avec leurs holdings
        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()
        
        alerts_created = 0
        
        for p in portfolios:
            # Récupérer les holdings
            h_result = await db.execute(select(Holding).where(Holding.portfolio_id == p.id))
            holdings = h_result.scalars().all()
            
            if not holdings:
                continue
                
            # Récupérer les prix live
            tickers = [h.ticker for h in holdings]
            live_prices = await get_all_prices(tickers)
            
            # Calculer la valeur totale et les poids actuels
            total_value = 0.0
            current_weights = {}
            
            for h in holdings:
                price_data = live_prices.get(h.ticker) or {}
                current_price = price_data.get("close", h.avg_buy_price)
                market_value = h.quantity * current_price
                total_value += market_value
                current_weights[h.ticker] = market_value
                
            if total_value == 0:
                continue
                
            # Normaliser les poids
            for t in current_weights:
                current_weights[t] /= total_value
                
            # Vérifier la dérive
            drift_detected = False
            max_drift = 0.0
            
            for h in holdings:
                target = h.weight_pct
                current = current_weights.get(h.ticker, 0.0)
                drift = abs(current - target)
                
                if drift > max_drift:
                    max_drift = drift
                    
                # Seuil de dérive : par défaut REBALANCE_DRIFT_THRESHOLD (5%)
                if drift > settings.REBALANCE_DRIFT_THRESHOLD:
                    drift_detected = True
                    
            if drift_detected:
                # Créer une alerte
                alert = Alert(
                    portfolio_id=p.id,
                    type="drift",
                    threshold=settings.REBALANCE_DRIFT_THRESHOLD
                )
                db.add(alert)
                alerts_created += 1
                log.info(f"Dérive détectée pour le portefeuille {p.id} (Max drift: {max_drift:.2%})")
                
        if alerts_created > 0:
            await db.commit()
            
        return alerts_created

@shared_task(name="tasks.rebalance_task.check_all_portfolios_drift")
def check_all_portfolios_drift():
    """
    Tâche Celery synchrone qui enveloppe la logique asynchrone.
    """
    log.info("Démarrage de la vérification des dérives de portefeuille...")
    
    # Exécuter la fonction async dans la boucle d'événements
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Si appelé depuis une thread où l'event loop tourne déjà
        future = asyncio.run_coroutine_threadsafe(_check_drift_async(), loop)
        alerts_created = future.result()
    else:
        alerts_created = asyncio.run(_check_drift_async())
        
    log.info(f"Vérification terminée. {alerts_created} alertes créées.")
    return {"status": "ok", "alerts_created": alerts_created}
