"""
Route de recommandation — POST /portfolio/{id}/recommend
Lance l'orchestrateur LangGraph et retourne la recommandation.
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.postgres import get_db
from app.models.portfolio import Portfolio, Holding, Recommendation
from app.models.user import User, RiskProfile
from app.agents.orchestrator import run_recommendation
from app.core.config import settings

router = APIRouter()


class RecommendRequest(BaseModel):
    question: str = "Analyse mon portefeuille et donne-moi des recommandations."

    model_config = {"json_schema_extra": {"example": {"question": "Dois-je rééquilibrer mon portefeuille ?"}}}


@router.post("/{portfolio_id}/recommend", summary="Lancer l'analyse multi-agents")
async def get_recommendation(
    portfolio_id: str,
    payload: RecommendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lance les 3 agents IA en parallèle (Quant + Analyste → Conseiller).
    Cible : réponse < 8 secondes.
    Monitoring : chaque run est tracé dans LangSmith.
    """
    start_time = time.time()

    # Récupérer le portefeuille
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portefeuille introuvable.")

    # Récupérer les tickers du portefeuille
    holdings_result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    holdings = holdings_result.scalars().all()
    tickers = [h.ticker for h in holdings] if holdings else settings.PRICE_TICKERS[:6]

    # Récupérer le profil de risque
    profile_result = await db.execute(
        select(RiskProfile)
        .where(RiskProfile.user_id == current_user.id)
        .order_by(RiskProfile.created_at.desc())
        .limit(1)
    )
    risk_profile_obj = profile_result.scalar_one_or_none()
    risk_profile = risk_profile_obj.profile_type if risk_profile_obj else "modéré"

    # ── Lancer les agents ────────────────────────────────────
    try:
        final_state = await run_recommendation(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            risk_profile=risk_profile,
            tickers=tickers,
            question=payload.question,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur du système multi-agents : {str(e)}"
        )

    elapsed = round(time.time() - start_time, 2)

    # Sauvegarder en DB
    try:
        recommendation_text = final_state.get("recommendation", "{}")
        parsed = json.loads(recommendation_text)

        rec = Recommendation(
            portfolio_id=portfolio_id,
            content=parsed.get("explanation", recommendation_text),
            shap_data=final_state.get("shap_data"),
            sentiment_score=sum(final_state.get("sentiment_scores", {}).values()) or None,
            final_allocation=final_state.get("final_allocation"),
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)

    except Exception as e:
        # Ne pas bloquer la réponse si la sauvegarde échoue
        parsed = {}

    return {
        "portfolio_id": portfolio_id,
        "risk_profile": risk_profile,
        "recommendation": final_state.get("recommendation"),
        "final_allocation": final_state.get("final_allocation", {}),
        "sharpe_ratio": final_state.get("sharpe_ratio"),
        "shap_data": final_state.get("shap_data"),
        "sentiment_scores": final_state.get("sentiment_scores"),
        "esg_scores": final_state.get("esg_scores"),
        "graph_context": final_state.get("graph_context"),
        "latency_seconds": elapsed,
        "errors": {
            k: v for k, v in {
                "quant": final_state.get("quant_error"),
                "analyst": final_state.get("analyst_error"),
                "advisor": final_state.get("advisor_error"),
            }.items() if v
        },
    }
