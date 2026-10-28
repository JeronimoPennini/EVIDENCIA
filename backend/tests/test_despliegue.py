"""
EvidencIA — Tests de la configuración de despliegue

Cubren lo que solo se rompe cuando la app sale de localhost:
el puerto que inyecta el hosting, la lista de orígenes CORS y el arranque
`server_start.py`.
"""

import pytest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from main import app
from app.config import Settings, get_settings

client = TestClient(app)


def _kwargs_cors() -> dict:
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware.kwargs
    raise AssertionError("La app no montó CORSMiddleware")


# --------------------------------------------------------------------------- puerto


def test_el_puerto_del_host_gana_sobre_el_default(monkeypatch):
    """Render/Railway/Docker pasan PORT; server_start debe escuchar ahí."""
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.delenv("BACKEND_PORT", raising=False)
    settings = Settings(_env_file=None)
    assert settings.backend_port == 10000


def test_backend_port_sigue_servindo_para_local(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("BACKEND_PORT", "8123")
    settings = Settings(_env_file=None)
    assert settings.backend_port == 8123


# --------------------------------------------------------------------------- orígenes


def test_los_orígenes_se_normalizan_y_sin_entradas_vacias(monkeypatch):
    monkeypatch.setenv(
        "ALLOWED_ORIGINS", " https://evidencia.app ,, http://localhost:3000 "
    )
    settings = Settings(_env_file=None)
    assert settings.origins_list == ["https://evidencia.app", "http://localhost:3000"]
    assert settings.origins_abiertos is False


def test_asterisco_detecta_api_abierta(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    assert Settings(_env_file=None).origins_abiertos is True


def test_los_puertos_efimeros_de_flutter_web_siguen_permitidos_por_default():
    """Sin configuración, el regex de localhost debe seguir vigente."""
    settings = Settings(_env_file=None)
    kwargs = _kwargs_cors()
    assert kwargs["allow_origin_regex"] == settings.cors_origin_regex
    assert "localhost" in kwargs["allow_origin_regex"]


# --------------------------------------------------------------------------- CORS real


def test_preflight_de_un_puerto_efimero_de_chrome_se_autoriza():
    origen = "http://localhost:53412"
    respuesta = client.options(
        "/api/v1/search/pico",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.headers.get("access-control-allow-origin") == origen


def test_un_origen_ajeno_no_recibe_permiso():
    if get_settings().origins_abiertos:
        pytest.skip("CORS abierto a propósito mediante ALLOWED_ORIGINS=*")
    origen = "https://no-es-mi-app.example"
    respuesta = client.options(
        "/api/v1/search/pico",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert respuesta.headers.get("access-control-allow-origin") != origen


def test_health_reporta_los_orígenes_activos():
    data = client.get("/health").json()
    assert "cors_origenes" in data
    assert "cors_regex" in data


# --------------------------------------------------------------------------- arranque


def test_server_start_usa_el_puerto_configurado_y_keep_alive_largo(monkeypatch):
    import server_start

    llamado: dict = {}

    def espía(app_path, **kwargs):
        llamado["app_path"] = app_path
        llamado.update(kwargs)

    monkeypatch.setattr(server_start.uvicorn, "run", espía)

    class _Settings:
        backend_port = 9999

    monkeypatch.setattr(server_start, "get_settings", lambda: _Settings())

    server_start.main()

    assert llamado["app_path"] == "main:app"
    assert llamado["host"] == "0.0.0.0"
    assert llamado["port"] == 9999
    assert llamado["timeout_keep_alive"] >= 60  # la síntesis por IA demora ~20-30 s
