"""
Routes portefeuille.
GET  /portfolio/           → Liste des portefeuilles de l'utilisateur
POST /portfolio/           → Créer un portefeuille
GET  /portfolio/{id}       → Détails d'un portefeuille
DELETE /portfolio/{id}     → Supprimer un portefeuille
"""
import json
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.postgres import get_db
from app.db.redis_client import get_all_prices
from app.models.portfolio import Portfolio, Holding
from app.models.user import User

router = APIRouter()


class PortfolioCreate(BaseModel):
    name: str
    capital: float = 0.0

    model_config = {"json_schema_extra": {"example": {"name": "Mon Portefeuille", "capital": 10000.0}}}


class PortfolioResponse(BaseModel):
    id: str
    name: str
    capital: float
    holdings: list[dict] = []

    model_config = {"from_attributes": True}


@router.get("/", summary="Liste des portefeuilles")
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolios = result.scalars().all()
    return [{"id": p.id, "name": p.name, "capital": p.capital} for p in portfolios]


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Créer un portefeuille")
async def create_portfolio(
    payload: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    portfolio = Portfolio(
        user_id=current_user.id,
        name=payload.name,
        capital=payload.capital,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return {"id": portfolio.id, "name": portfolio.name, "capital": portfolio.capital}


@router.post("/import", status_code=status.HTTP_201_CREATED, summary="Créer un portefeuille depuis un CSV")
async def import_portfolio_csv(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except Exception:
        decoded = content.decode("utf-8")

    reader = csv.DictReader(io.StringIO(decoded))
    
    holdings_data = []
    total_capital = 0.0
    
    for row in reader:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        try:
            # Support both French and English column names
            qty = float(row.get("quantite") or row.get("quantity") or row.get("qty") or 0)
            price = float(row.get("prix_achat_moyen") or row.get("avg_buy_price") or row.get("price") or 0)
        except (ValueError, TypeError):
            continue
            
        if qty > 0:
            holdings_data.append({"ticker": ticker, "quantity": qty, "price": price})
            total_capital += qty * price
            
    if not holdings_data:
        raise HTTPException(status_code=400, detail="CSV invalide ou vide. Colonnes attendues: ticker, quantite, prix_achat_moyen")
        
    portfolio = Portfolio(
        user_id=current_user.id,
        name=name,
        capital=round(total_capital, 2),
    )
    db.add(portfolio)
    await db.flush()
    
    for h in holdings_data:
        weight = (h["quantity"] * h["price"]) / total_capital if total_capital > 0 else 0
        holding = Holding(
            portfolio_id=portfolio.id,
            ticker=h["ticker"],
            quantity=h["quantity"],
            avg_buy_price=h["price"],
            weight_pct=round(weight, 4)
        )
        db.add(holding)
        
    await db.commit()
    await db.refresh(portfolio)
    return {"id": portfolio.id, "name": portfolio.name, "capital": portfolio.capital, "holdings_count": len(holdings_data)}



@router.get("/{portfolio_id}", summary="Détails d'un portefeuille")
async def get_portfolio(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne le portefeuille avec les holdings et les prix live depuis Redis."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portefeuille introuvable.")

    # Holdings
    holdings_result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    holdings = holdings_result.scalars().all()

    # Prix live depuis Redis
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
            "id": h.id,
            "ticker": h.ticker,
            "quantity": h.quantity,
            "avg_buy_price": h.avg_buy_price,
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "weight_pct": h.weight_pct,
            "pnl_pct": round((current_price / h.avg_buy_price - 1) * 100, 2) if h.avg_buy_price > 0 else 0,
        })

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "capital": portfolio.capital,
        "total_market_value": round(total_value, 2),
        "holdings": holdings_data,
    }

