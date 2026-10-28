"""
EvidencIA — Tests del cliente Gemini (sin red).
Cubren las dos fallas silenciosas que dejaban la IA desactivada:
verificación SSL de Windows y modelos obsoletos/saturados.
"""

import asyncio
import ssl

import pytest

from app.services import gemini_service


class _Respuesta:
    def __init__(self, texto):
        self.text = texto


class _ModelosFake:
    """Simula client.aio.models con un mapa modelo -> excepción o texto."""

    def __init__(self, comportamientos, registro):
        self.comportamientos = comportamientos
        self.registro = registro

    async def generate_content(self, model, contents, config):
        self.registro.append((model, config.temperature, config.max_output_tokens))
        comportamiento = self.comportamientos.get(model)
        if isinstance(comportamiento, Exception):
            raise comportamiento
        return _Respuesta(comportamiento)


class _ClienteFake:
    def __init__(self, modelos):
        self.aio = type("Aio", (), {"models": modelos})()


def _instalar(monkeypatch, comportamientos, registro):
    modelos = _ModelosFake(comportamientos, registro)
    monkeypatch.setattr(gemini_service, "_get_client", lambda: _ClienteFake(modelos))
    return registro


def test_ssl_del_sistema_configurado():
    """El cliente debe verificar SSL con el trust store de Windows."""
    contexto = gemini_service._SSL_VERIFY
    es_contexto = isinstance(contexto, ssl.SSLContext)
    es_predeterminado = contexto is True
    assert es_contexto or es_predeterminado


def test_get_client_configura_ssl_y_timeout(monkeypatch):
    """El cliente se construye con el contexto SSL del sistema y timeout holgado."""

    class ClienteEspia:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    def _capturar(**kwargs):
        captured.append(ClienteEspia(**kwargs))
        return captured[-1]

    captured = []
    monkeypatch.setattr(gemini_service.genai, "Client", _capturar)

    cliente = gemini_service._get_client()

    opciones = captured[0].kwargs["http_options"]
    assert opciones.async_client_args["verify"] is gemini_service._SSL_VERIFY
    assert opciones.async_client_args["trust_env"] is True
    assert opciones.timeout >= 60_000
    assert isinstance(cliente, ClienteEspia)
    # La clave se lee de settings y nunca se expone en /health ni en el cliente.
    assert "api_key" in captured[0].kwargs


def test_sin_clave_el_cliente_avisa_donde_configurarla(monkeypatch):
    from app.config import Settings

    monkeypatch.setattr(
        gemini_service, "get_settings", lambda: Settings(gemini_api_key="")
    )

    with pytest.raises(ValueError, match="aistudio.google.com"):
        gemini_service._get_client()


def test_modelo_obsoleto_usa_el_respaldado(monkeypatch):
    """404 en el modelo configurado -> reintenta con el respaldo y lo reporta."""
    monkeypatch.setattr(gemini_service, "_candidatos", lambda: ["modelo-1", "respaldo-1"])
    monkeypatch.setattr(gemini_service, "_modelo_activo", "", raising=True)
    registro = []
    _instalar(
        monkeypatch,
        {"modelo-1": RuntimeError("404 NOT_FOUND: no longer available"),
         "respaldo-1": "Texto del respaldo"},
        registro,
    )

    texto = asyncio.run(gemini_service.generar_sintesis("prompt"))

    assert texto == "Texto del respaldo"
    assert [m for m, _, _ in registro] == ["modelo-1", "respaldo-1"]
    assert gemini_service.get_nombre_modelo() == "respaldo-1"
    # Temperatura baja y techo de tokens: comportamiento esperado del wrapper.
    assert all(temperatura == 0.3 and max_tokens == 4096 for _, temperatura, max_tokens in registro)


def test_saturado_reintenta_antes_de_cambiar_de_modelo(monkeypatch):
    """503 es transitorio: se prueba el mismo modelo otra vez antes de rendirse."""
    monkeypatch.setattr(gemini_service, "_candidatos", lambda: ["modelo-1", "respaldo-1"])
    monkeypatch.setattr(gemini_service, "_modelo_activo", "", raising=True)
    intentos = []

    class _Modelos:
        async def generate_content(self, model, contents, config):
            intentos.append(model)
            if len(intentos) == 1:
                raise RuntimeError("503 UNAVAILABLE: high demand")
            return _Respuesta("OK")

    monkeypatch.setattr(gemini_service, "_get_client", lambda: _ClienteFake(_Modelos()))
    texto = asyncio.run(gemini_service.generar_sintesis("prompt"))

    assert texto == "OK"
    assert intentos == ["modelo-1", "modelo-1"]


def test_sin_ningun_modelo_disponible_falla_visiblemente(monkeypatch):
    """No debe devolver vacío: el error se propaga con los modelos probados."""
    monkeypatch.setattr(gemini_service, "_candidatos", lambda: ["modelo-1", "respaldo-1"])
    _instalar(monkeypatch, {}, [])  # todo modelo devuelve texto vacío

    with pytest.raises(RuntimeError, match="Gemini no pudo generar"):
        asyncio.run(gemini_service.generar_sintesis("prompt"))
