"""
Configuration de la base de données PostgreSQL via SQLAlchemy (asynchrone).
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

log = logging.getLogger(__name__)

# Base pour les modèles SQLAlchemy
Base = declarative_base()

# Création de l'engine asynchrone PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

# Factory pour créer des sessions asynchrones
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def init_db() -> None:
    """Crée toutes les tables définies dans les modèles si elles n'existent pas."""
    async with engine.begin() as conn:
        log.info("Initialisation de la base de données PostgreSQL (création des tables)...")
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession: # type: ignore
    """
    Générateur de session de base de données asynchrone (Dependency FastAPI).
    Assure la fermeture automatique de la session après la requête.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
