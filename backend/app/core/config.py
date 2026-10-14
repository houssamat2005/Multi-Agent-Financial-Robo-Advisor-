"""
Configuration centrale de l'application.
Toutes les variables d'environnement sont lues ici via pydantic-settings.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── PostgreSQL ──────────────────────────────────────────────
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres123"
    POSTGRES_DB: str = "roboadvisor"
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v: str, info) -> str:
        if v:
            return v
        data = info.data
        return (
            f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:"
            f"{data.get('POSTGRES_PASSWORD')}@localhost:5432/"
            f"{data.get('POSTGRES_DB')}"
        )

    # ── Redis ───────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Neo4j ───────────────────────────────────────────────────
    NEO4J_URL: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j123"

    # ── ChromaDB ────────────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # ── Kafka ───────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # ── JWT ─────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "robo_advisor_super_secret_jwt_key_2024_dev"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── APIs externes ────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    # ── LangSmith ────────────────────────────────────────────────
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "robo-advisor"

    # ── MLflow ───────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # ── Ingestion ────────────────────────────────────────────────
    PRICE_POLL_INTERVAL_SECONDS: int = 60
    NEWS_POLL_INTERVAL_MINUTES: int = 15
    PRICE_TICKERS: List[str] = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "TSLA", "META", "BRK-B", "JPM", "V", "SPY", "QQQ"
    ]
    LOOKBACK_DAYS: int = 504

    # ── Agents ───────────────────────────────────────────────────
    REBALANCE_DRIFT_THRESHOLD: float = 0.05
    MAX_RECOMMENDATION_LATENCY_SECONDS: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
