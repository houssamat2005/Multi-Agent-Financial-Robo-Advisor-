import os
from celery import Celery

from app.core.config import settings

# Configuration de Celery
celery_app = Celery(
    "robo_advisor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.rebalance_task"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    # Planification périodique (Beat)
    beat_schedule={
        "check-portfolio-drift-daily": {
            "task": "tasks.rebalance_task.check_all_portfolios_drift",
            # Exécution tous les jours à 18h00 CET (après la clôture des marchés européens)
            "schedule": 86400.0, # Pour le dev on pourrait mettre 60.0 (toutes les minutes)
            # En production on utiliserait crontab(hour=18, minute=0)
        },
    }
)

if __name__ == "__main__":
    celery_app.start()
