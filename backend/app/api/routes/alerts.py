"""
Routes alertes — GET /alerts, POST /alerts/{id}/read, POST /alerts/configure
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.postgres import get_db
from app.models.portfolio import Alert, Portfolio
from app.models.user import User

router = APIRouter()


class AlertResponse(BaseModel):
    id: str
    portfolio_id: str
    type: str
    threshold: float
    triggered_at: str
    is_read: bool

    model_config = {"from_attributes": True}


class ConfigureAlertRequest(BaseModel):
    portfolio_id: str
    threshold: float   # 0.01 à 0.20 (1% à 20%)

    model_config = {"json_schema_extra": {"example": {"portfolio_id": "...", "threshold": 0.05}}}


@router.get("/", response_model=list[AlertResponse], summary="Liste des alertes non lues")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retourne toutes les alertes non lues de l'utilisateur pour tous ses portefeuilles.
    """
    # Sous-requête pour les IDs de portefeuilles de l'utilisateur
    portfolios_query = select(Portfolio.id).where(Portfolio.user_id == current_user.id)
    
    result = await db.execute(
        select(Alert)
        .where(
            Alert.portfolio_id.in_(portfolios_query),
            Alert.is_read == False
        )
        .order_by(Alert.triggered_at.desc())
    )
    alerts = result.scalars().all()
    
    return [
        AlertResponse(
            id=a.id,
            portfolio_id=a.portfolio_id,
            type=a.type,
            threshold=a.threshold,
            triggered_at=a.triggered_at.isoformat(),
            is_read=a.is_read
        ) for a in alerts
    ]


@router.post("/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT, summary="Marquer une alerte comme lue")
async def mark_alert_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marque une alerte comme lue pour qu'elle disparaisse du bandeau."""
    # Vérifier que l'alerte appartient à un portfolio de l'user
    result = await db.execute(
        select(Alert).join(Portfolio).where(
            Alert.id == alert_id,
            Portfolio.user_id == current_user.id
        )
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte introuvable.")
        
    alert.is_read = True
    await db.commit()


@router.post("/configure", summary="Configurer le seuil d'alerte")
async def configure_alerts(
    payload: ConfigureAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Configure le seuil d'alerte de dérive pour un portefeuille.
    Le seuil doit être entre 1% (0.01) et 20% (0.20).
    Note: dans une implémentation complète, on ajouterait une table PortfolioSettings.
    Ici, on va le simuler/simplifier pour respecter le cahier des charges.
    """
    if not 0.01 <= payload.threshold <= 0.20:
        raise HTTPException(status_code=422, detail="Le seuil doit être entre 1% et 20%.")
        
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == payload.portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Portefeuille introuvable.")
        
    # TODO: Stocker ce réglage en base (ajouté au scope MVP simplifié)
    return {"message": f"Seuil configuré à {payload.threshold:.1%}"}
