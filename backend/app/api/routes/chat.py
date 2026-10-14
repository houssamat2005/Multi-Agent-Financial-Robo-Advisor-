"""
Route de Chat IA — POST /chat/{portfolio_id}
L'investisseur peut discuter avec l'agent expert en finance.
L'agent connaît le portefeuille de l'utilisateur et les données de marché.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from groq import Groq

from app.api.dependencies import get_current_user
from app.db.postgres import get_db
from app.db.redis_client import get_all_prices
from app.models.portfolio import Portfolio, Holding
from app.models.user import User
from app.core.config import settings

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]


SYSTEM_PROMPT = """Tu es un conseiller financier IA expert, précis et pédagogue.
Tu as accès aux données en temps réel du portefeuille de l'investisseur.
Tu dois analyser ces données et répondre aux questions de l'investisseur de façon claire, structurée et en français.

Règles :
1. Sois concis et précis. Utilise des données chiffrées quand c'est pertinent.
2. Si l'utilisateur demande une recommandation, base-toi sur les données du portefeuille.
3. Réponds toujours en français.
4. Tu peux suggérer des actions concrètes (acheter, vendre, rééquilibrer).
5. Signale les risques ou les opportunités détectées.
"""


@router.post("/{portfolio_id}")
async def chat_with_advisor(
    portfolio_id: str,
    payload: ChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    # Récupérer les holdings
    holdings_result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    holdings = holdings_result.scalars().all()

    # Prix live
    tickers = [h.ticker for h in holdings]
    live_prices = await get_all_prices(tickers) if tickers else {}

    # Construire le contexte portefeuille
    holdings_summary = []
    total_value = 0.0
    for h in holdings:
        price_data = live_prices.get(h.ticker) or {}
        current_price = price_data.get("close", h.avg_buy_price)
        market_value = h.quantity * current_price
        total_value += market_value
        pnl = round((current_price / h.avg_buy_price - 1) * 100, 2) if h.avg_buy_price > 0 else 0
        holdings_summary.append(
            f"  - {h.ticker}: {h.quantity} unités, prix achat {h.avg_buy_price:.2f}$, "
            f"prix actuel {current_price:.2f}$, valeur {market_value:.2f}$, PnL {pnl:+.2f}%"
        )

    portfolio_context = f"""
=== PORTEFEUILLE DE L'INVESTISSEUR ===
Nom : {portfolio.name}
Capital Initial : {portfolio.capital:.2f}$
Valeur Actuelle Totale : {total_value:.2f}$
Plus/Moins-value : {(total_value - portfolio.capital):+.2f}$ ({((total_value/portfolio.capital - 1)*100) if portfolio.capital > 0 else 0:+.1f}%)

Actifs :
{chr(10).join(holdings_summary) if holdings_summary else "  (Aucun actif dans ce portefeuille)"}
"""

    system_with_context = SYSTEM_PROMPT + "\n" + portfolio_context

    # Construire les messages pour Groq
    messages = [{"role": "system", "content": system_with_context}]
    
    # Ajouter l'historique (max 10 derniers messages)
    for msg in payload.history[-10:]:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Ajouter le message actuel
    messages.append({"role": "user", "content": payload.message})

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=600,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur LLM : {str(e)}")

    return {
        "reply": reply,
        "portfolio_context": {
            "total_value": round(total_value, 2),
            "capital": portfolio.capital,
            "holdings_count": len(holdings),
        }
    }
