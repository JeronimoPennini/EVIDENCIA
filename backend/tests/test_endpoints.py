"""
EvidencIA — Tests de los endpoints FastAPI
Usa el TestClient de FastAPI para probar los routers sin levantar un servidor real.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    """El endpoint /health debe responder 200 con los campos esperados."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "gemini_configurado" in data
    assert "modelo_ia" in data


def test_search_validation_query_corta():
    """El endpoint /search debe rechazar queries de menos de 3 caracteres."""
    response = client.post("/api/v1/search", json={"query": "ab"})
    assert response.status_code == 422  # Unprocessable Entity (Pydantic)


def test_search_validation_max_results_fuera_de_rango():
    """El endpoint /search debe rechazar max_results > 50."""
    response = client.post(
        "/api/v1/search", json={"query": "metformin", "max_results": 100}
    )
    assert response.status_code == 422


def test_synthesize_validation_sin_pmids():
    """El endpoint /synthesize debe rechazar una lista de PMIDs vacía."""
    response = client.post(
        "/api/v1/synthesize",
        json={"pmids": [], "pregunta_clinica": "¿Cuál es la eficacia del tratamiento?"},
    )
    assert response.status_code == 422


def test_synthesize_validation_pregunta_corta():
    """El endpoint /synthesize debe rechazar preguntas menores a 10 caracteres."""
    response = client.post(
        "/api/v1/synthesize",
        json={"pmids": ["12345678"], "pregunta_clinica": "corta"},
    )
    assert response.status_code == 422


def test_docs_disponibles():
    """La documentación Swagger debe estar disponible."""
    response = client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_integration_pubmed():
    """
    Test de integración: búsqueda real en PubMed a través del servicio directamente.
    Se prueba el servicio en vez del TestClient para evitar incompatibilidades async.
    """
    from app.services.pubmed_service import buscar_articulos
    resultado = await buscar_articulos(query="hypertension treatment", max_results=3)
    assert resultado.total_encontrados > 0
    assert len(resultado.articulos) <= 3
    assert resultado.articulos[0].pmid != ""
