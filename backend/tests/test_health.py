"""
Tests du health check FastAPI.
Vérifie que l'endpoint /health répond 200.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    """L'endpoint /health doit toujours retourner 200."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_has_services_key():
    """La réponse /health doit contenir la clé 'services'."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "env" in data


@pytest.mark.asyncio
async def test_openapi_docs_available():
    """/docs doit retourner 200 (OpenAPI disponible)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/docs")
    assert response.status_code == 200
