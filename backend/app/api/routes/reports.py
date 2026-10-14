"""
Routes pour les rapports PDF.
POST /reports/generate
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.postgres import get_db
from app.db.redis_client import get_all_prices
from app.models.portfolio import Portfolio, Holding, Recommendation
from app.models.user import User
from app.services.pdf_generator import generate_portfolio_pdf

router = APIRouter()


class GenerateReportRequest(BaseModel):
    portfolio_id: str


@router.post("/generate", summary="Générer un rapport PDF de portefeuille")
async def generate_report(
    payload: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Génère un rapport PDF avec l'allocation, les perfs et les recos."""
    # Récupérer le portefeuille
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == payload.portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portefeuille introuvable.")

    # Holdings
    h_result = await db.execute(select(Holding).where(Holding.portfolio_id == portfolio.id))
    holdings = h_result.scalars().all()
    
    tickers = [h.ticker for h in holdings]
    live_prices = await get_all_prices(tickers) if tickers else {}
    
    holdings_data = []
    total_value = 0.0
    for h in holdings:
        price_data = live_prices.get(h.ticker) or {}
        current_price = price_data.get("close", h.avg_buy_price)
        market_value = h.quantity * current_price
        total_value += market_value
        holdings_data.append({
            "ticker": h.ticker,
            "quantity": h.quantity,
            "avg_buy_price": h.avg_buy_price,
            "current_price": current_price,
            "market_value": market_value,
            "weight_pct": h.weight_pct
        })
        
    # Recommandation récente (optionnelle)
    rec_result = await db.execute(
        select(Recommendation)
        .where(Recommendation.portfolio_id == portfolio.id)
        .order_by(Recommendation.created_at.desc())
        .limit(1)
    )
    rec = rec_result.scalar_one_or_none()
    recommendation_text = rec.content if rec else ""
    
    # Génération du PDF
    pdf_buffer = generate_portfolio_pdf(
        user_email=current_user.email,
        portfolio_name=portfolio.name,
        capital=total_value,
        holdings=holdings_data,
        recommendation_text=recommendation_text,
    )
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=rapport_{portfolio.name.replace(' ', '_')}.pdf"
        }
    )
