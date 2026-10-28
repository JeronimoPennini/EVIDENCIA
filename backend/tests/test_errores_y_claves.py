"""
EvidencIA — Fugas de credenciales y tolerancia a una API key inválida

Dos cosas que sólo importan cuando la API está publicada:
1. El detalle de error que ve el cliente no puede contener la URL de NCBI
   (esa URL lleva `api_key=` en el query string).
2. Una NCBI_API_KEY mal copiada en el hosting no puede dejar la app sin buscar.
"""

import httpx
import pytest

from app.errors import resumen_error
from app.services import pubmed_service


class _Respuesta:
    """Respuesta mínima de httpx para probar _get sin red."""

    def __init__(self, status_code: int, cuerpo: str = "{}"):
        self.status_code = status_code
        self._cuerpo = cuerpo
        self.text = cuerpo

    def json(self):
        import json

        return json.loads(self._cuerpo)

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", pubmed_service.NCBI_BASE)
            raise httpx.HTTPStatusError(
                f"Client error {self.status_code}", request=request, response=self
            )


class _Cliente:
    """Registra qué params se enviaron y responde 400 sólo si va api_key."""

    def __init__(self):
        self.envios: list[bool] = []

    async def get(self, url, params=None):
        lleva_clave = "api_key" in (params or {})
        self.envios.append(lleva_clave)
        if lleva_clave:
            return _Respuesta(400, '{"error":"API key invalid"}')
        return _Respuesta(200, '{"esearchresult":{"count":"7","idlist":["123"]}}')


# ------------------------------------------------------------------ fugas


def test_el_resumen_de_error_no_filtra_la_api_key():
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        "?api_key=SECRETO_QUE_NO_DEBE_SALIR&db=pubmed&term=metformin"
    )
    request = httpx.Request("GET", url)
    response = httpx.Response(400, request=request, text='{"error":"API key invalid"}')
    error = httpx.HTTPStatusError("bad", request=request, response=response)

    mensaje = resumen_error(error)

    assert "SECRETO_QUE_NO_DEBE_SALIR" not in mensaje
    assert "api_key" not in mensaje
    assert "400" in mensaje
    assert "NCBI PubMed" in mensaje


def test_el_resumen_de_error_cubre_red_y_errores_genericos():
    red = httpx.ConnectError("timed out")
    assert "red o tiempo de espera" in resumen_error(red)
    assert resumen_error(ValueError("falta la pregunta")).startswith("ValueError")


def test_la_url_del_error_no_aparece_en_el_detalle_del_endpoint():
    """Regresión: /api/v1/search devolvía 502 con la URL de NCBI incluida."""
    from fastapi.testclient import TestClient
    from main import app

    class _SinRed:
        async def buscar_articulos(self, **kwargs):
            request = httpx.Request("GET", "https://eutils.ncbi.nlm.nih.gov/x?api_key=ZZ")
            raise httpx.HTTPStatusError(
                "boom", request=request, response=httpx.Response(400, request=request)
            )

    original = pubmed_service.buscar_articulos
    pubmed_service.buscar_articulos = _SinRed().buscar_articulos
    try:
        client = TestClient(app)
        respuesta = client.post("/api/v1/search", json={"query": "metformina"})
    finally:
        pubmed_service.buscar_articulos = original

    assert respuesta.status_code == 502
    assert "ZZ" not in respuesta.text


# ------------------------------------------------------- clave inválida


@pytest.mark.asyncio
async def test_clave_invalida_reintenta_sin_clave_y_sigue_funcionando(monkeypatch):
    monkeypatch.setattr(pubmed_service, "_CLAVE_INVALIDA", False)
    cliente = _Cliente()

    respuesta = await pubmed_service._get(
        cliente, "esearch.fcgi", {"api_key": "x", "db": "pubmed", "term": "metformina"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["esearchresult"]["count"] == "7"
    assert cliente.envios == [True, False]
    assert pubmed_service._CLAVE_INVALIDA is True


def _settings_falsos(clave: str):
    class S:
        ncbi_api_key = clave
        ncbi_email = "algo@dominio.com"

    return S()


def test_sin_clave_no_se_envia_el_parametro(monkeypatch):
    monkeypatch.setattr(pubmed_service, "_CLAVE_INVALIDA", False)
    monkeypatch.setattr(pubmed_service, "get_settings", lambda: _settings_falsos(""))
    assert "api_key" not in pubmed_service._build_params({"db": "pubmed"})

    monkeypatch.setattr(
        pubmed_service, "get_settings", lambda: _settings_falsos("tu_clave_aqui")
    )
    assert "api_key" not in pubmed_service._build_params({"db": "pubmed"})


def test_clave_valida_se_envia_hasta_que_ncbi_la_rechaza(monkeypatch):
    monkeypatch.setattr(pubmed_service, "_CLAVE_INVALIDA", False)
    monkeypatch.setattr(pubmed_service, "get_settings", lambda: _settings_falsos("abcd"))
    assert pubmed_service._build_params({"db": "pubmed"}).get("api_key") == "abcd"

    monkeypatch.setattr(pubmed_service, "_CLAVE_INVALIDA", True)
    assert "api_key" not in pubmed_service._build_params({"db": "pubmed"})
    estado = pubmed_service.estado_ncbi()
    assert estado["api_key_configurada"] is True
    assert estado["api_key_aceptada"] is False
    assert estado["limite_por_segundo"] == 3
