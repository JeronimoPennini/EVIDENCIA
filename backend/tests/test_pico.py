"""
EvidencIA — Tests del servicio y router PICO
Verifica construcción de preguntas clínicas, queries booleanas y endpoint PICO.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.services.pico_service import (
    construir_pregunta_clinica,
    construir_query_fallback,
    _aplicar_filtro_estudio,
)

client = TestClient(app)


def test_construir_pregunta_clinica():
    pregunta = construir_pregunta_clinica(
        poblacion="adultos con diabetes tipo 2",
        intervencion="empagliflozina",
        comparacion="placebo",
        outcome="mortalidad cardiovascular",
    )
    assert "adultos con diabetes tipo 2" in pregunta
    assert "empagliflozina" in pregunta
    assert "en comparación con placebo" in pregunta
    assert "mortalidad cardiovascular" in pregunta


def test_construir_pregunta_clinica_sin_comparacion():
    pregunta = construir_pregunta_clinica(
        poblacion="pacientes con asma leve",
        intervencion="budesonida",
        comparacion="",
        outcome="crisis asmáticas",
    )
    assert "pacientes con asma leve" in pregunta
    assert "budesonida" in pregunta
    assert "comparación" not in pregunta
    assert "crisis asmáticas" in pregunta


def test_construir_query_fallback():
    query = construir_query_fallback(
        poblacion="heart failure",
        intervencion="dapagliflozin",
        comparacion="placebo",
        outcome="hospitalization",
        filtro_estudio="all",
    )
    assert "(heart failure)" in query
    assert "(dapagliflozin)" in query
    assert "(placebo)" in query
    assert "(hospitalization)" in query
    assert " AND " in query


def test_aplicar_filtro_estudio():
    query_base = "(diabetes) AND (metformin)"
    q_rct = _aplicar_filtro_estudio(query_base, "rct")
    assert "clinical trial[Filter]" in q_rct

    q_sr = _aplicar_filtro_estudio(query_base, "systematic_review")
    assert "systematic review[Filter]" in q_sr


def test_endpoint_pico_validation_error():
    # Población muy corta
    resp = client.post(
        "/api/v1/search/pico",
        json={
            "poblacion": "a",
            "intervencion": "metformin",
            "outcome": "mortality",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_pico_integration():
    resp = client.post(
        "/api/v1/search/pico",
        json={
            "poblacion": "hypertension",
            "intervencion": "losartan",
            "comparacion": "placebo",
            "outcome": "blood pressure",
            "filtro_estudio": "rct",
            "max_results": 2,
            "optimizar_con_ia": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "articulos" in data
    assert "pregunta_clinica" in data
    assert "query_pubmed" in data
    assert data["total_encontrados"] >= 0


def test_la_ia_que_falla_deja_de_ser_silenciosa(monkeypatch):
    """
    Antes el except desnudo devolvía el fallback sin avisar: la app mostraba
    resultados "normales" aunque Gemini estuviera muerto. Ahora el aviso viaja
    en la respuesta para que el usuario sepa que buscó sin optimización por IA.
    """
    import asyncio

    from app.services import gemini_service, pico_service

    async def _reventar(prompt):
        raise gemini_service.ClaveGeminiInvalida()

    monkeypatch.setattr(pico_service, "_gemini_disponible", lambda settings: True)
    monkeypatch.setattr(gemini_service, "generar_sintesis", _reventar)
    monkeypatch.setattr(pico_service, "ultimo_aviso_ia", None, raising=True)

    pregunta, query = asyncio.run(
        pico_service.traducir_y_optimizar_pico(
            poblacion="adultos con hipertensión",
            intervencion="inhibidores ECA",
            comparacion="",
            outcome="mortalidad",
        )
    )

    assert query == construir_query_fallback(
        "adultos con hipertensión", "inhibidores ECA", "", "mortalidad", "all"
    )
    assert pico_service.ultimo_aviso_ia and "GEMINI_API_KEY" in pico_service.ultimo_aviso_ia
