"""
Point d'entrée FastAPI — Robo-Advisor
"""
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.postgres import init_db
from app.db.redis_client import get_redis, close_redis
from app.db.neo4j_client import get_neo4j_driver, init_neo4j, close_neo4j
from app.db.chroma_client import get_chroma, close_chroma

from app.api.routes import auth, portfolio, recommendations, backtesting, alerts, onboarding, market, reports, chat

log = structlog.get_logger()

# ── Lifespan (startup / shutdown) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise et ferme toutes les connexions DB au démarrage/arrêt.
    """
    log.info("startup.begin", env=settings.APP_ENV)

    # ── Startup ─────────────────────────────────────────────
    # Init PostgreSQL
    await init_db()
    log.info("startup.db.ok")

    try:
        await get_redis()
        log.info("startup.redis.ok")
    except Exception as e:
        log.warning("startup.redis.failed", error=str(e))

    try:
        await init_neo4j()
        log.info("startup.neo4j.ok")
    except Exception as e:
        log.warning("startup.neo4j.failed", error=str(e))

    log.info("startup.complete")
    yield

    # ── Shutdown ─────────────────────────────────────────────
    log.info("shutdown.begin")
    await close_redis()
    await close_neo4j()
    await close_chroma()
    log.info("shutdown.complete")


# ── Application ───────────────────────────────────────────────
app = FastAPI(
    title="Robo-Advisor API",
    description="API du système multi-agents de conseil en investissement financier",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["Authentification"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portefeuille"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommandations"])
app.include_router(backtesting.router, prefix="/portfolio", tags=["Backtesting"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alertes"])
app.include_router(market.router, prefix="/market", tags=["Marché"])
app.include_router(reports.router, prefix="/reports", tags=["Rapports PDF"])
app.include_router(chat.router, prefix="/chat", tags=["Chat IA"])


# ── Health check ──────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Vérifie l'état de chaque service.
    Retourne 200 même si certains services sont dégradés (pour le monitoring).
    """
    status = {}

    # PostgreSQL
    try:
        from app.db.postgres import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {str(e)}"

    # Redis
    try:
        r = await get_redis()
        await r.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    # Neo4j
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            await session.run("RETURN 1")
        status["neo4j"] = "ok"
    except Exception as e:
        status["neo4j"] = f"error: {str(e)}"

    # ChromaDB
    try:
        client = await get_chroma()
        await client.heartbeat()
        status["chroma"] = "ok"
    except Exception as e:
        status["chroma"] = f"error: {str(e)}"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return {"status": overall, "services": status, "env": settings.APP_ENV}
