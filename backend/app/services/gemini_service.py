"""
EvidencIA — Servicio Gemini IA
Wrapper sobre el SDK google-genai para comunicarse con Gemini API (capa gratuita).
SDK de referencia: https://github.com/googleapis/python-genai
Las claves API se leen exclusivamente desde la configuración del backend.

Dos detalles de entorno que rompían la llamada y se degradaban en silencio:
- En Windows con Python 3.14 el trust store del sistema no está en el certificado
  por defecto de httpx: se inyecta el contexto SSL de `truststore`.
- Los nombres de modelo de Gemini quedan obsoletos (404) o saturan (503): se prueban
  respaldos en orden hasta que uno responda.
"""

import asyncio
import logging
import ssl

from google import genai
from google.genai import types

from app.config import get_settings

# Verificación SSL con los certificados del sistema (Windows / Python 3.14).
try:
    import truststore

    _SSL_VERIFY: object = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:  # pragma: no cover - other platforms
    _SSL_VERIFY = True

# Orden de respaldo si el modelo configurado no está disponible para la cuenta.
# Se puede reemplazar entero sin tocar código con la variable GEMINI_MODELOS.
_MODELOS_RESPALDO = ("gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash")

# Códigos que conviene reintentar antes de pasar al siguiente modelo.
_TRANSITORIOS = ("503", "429", "unavailable", "resource_exhausted", "high demand", "timeout")

# Modelo que respondió por última vez (para reportarlo en la respuesta).
_modelo_activo: str = ""

# Modelo "pegajoso": el último que respondió, para no volver a chocar contra el
# primero de la lista en cada consulta. Se despeja apenas falla.
_modelo_fijado: str = ""

# La clave fue rechazada por Google (401) en el último intento.
_clave_rechazada: bool = False


class ClaveGeminiInvalida(RuntimeError):
    """
    Google rechazó la API key (401 UNAUTHENTICATED).

    No es un problema de red ni de saturación: ningún modelo va a responder con
    esta clave, por eso se corta la cadena de reintentos y se informa al usuario
    qué variable hay que corregir.
    """

    def __init__(self) -> None:
        super().__init__(
            "La clave de Gemini (GEMINI_API_KEY) no es válida o fue revocada. "
            "Generá una nueva en https://aistudio.google.com/app/apikey y "
            "actualizala en el panel de Variables de entorno del servidor."
        )


def _es_fallo_de_clave(error: Exception) -> bool:
    """401 / 'API key not valid': la clave no existe, está mal copiada o revocada."""
    texto = str(error).lower()
    return any(
        marca in texto
        for marca in ("unauthenticated", "api key not valid", "invalid api key", "401")
    )


def clave_rechazada() -> bool:
    """True si Google devolvió 401 para la clave configurada en este proceso."""
    return _clave_rechazada


def estado_gemini() -> dict:
    """Diagnóstico de la clave para /health (nunca devuelve la clave)."""
    settings = get_settings()
    clave = (settings.gemini_api_key or "").strip()
    configurada = bool(clave) and not clave.startswith("tu_clave")
    return {
        "api_key_configurada": configurada,
        "api_key_aceptada": configurada and not _clave_rechazada,
        "modelo_configurado": settings.gemini_model,
        "modelo_usado": _modelo_activo or None,
        "modelo_pegajoso": _modelo_fijado or None,
        "cadena_de_modelos": _candidatos(),
    }


def _get_client() -> genai.Client:
    """Crea y retorna el cliente Gemini configurado con la API key del backend."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY no configurada. "
            "Obtené tu clave gratuita en https://aistudio.google.com/app/apikey "
            "y agregala al archivo .env"
        )
    return genai.Client(
        api_key=settings.gemini_api_key,
        # El SDK crea su propio httpx.AsyncClient: le pasamos el contexto SSL del sistema.
        http_options=types.HttpOptions(
            async_client_args={"verify": _SSL_VERIFY, "trust_env": True},
            timeout=120_000,
        ),
    )


def _es_transitorio(error: Exception) -> bool:
    texto = str(error).lower()
    return any(marca in texto for marca in _TRANSITORIOS)


def _soltar_si_fijado(modelo: str) -> None:
    """Deja de preferir un modelo que recién falló; el próximo éxito lo reemplaza."""
    global _modelo_fijado
    if modelo == _modelo_fijado:
        _modelo_fijado = ""


def _candidatos() -> list[str]:
    """
    Modelos a probar, en orden.

    El último que respondió va primero: Gemini satura por modelo durante minutos,
    y volver a arrancar desde el configurado en cada consulta significaba chocar
    otra vez contra el mismo 503 y pagar el reintento.
    """
    settings = get_settings()
    lista = [m.strip() for m in (settings.gemini_modelos or "").split(",") if m.strip()]
    if not lista:
        principal = (settings.gemini_model or "gemini-3.5-flash").strip()
        lista = [principal] + [m for m in _MODELOS_RESPALDO if m != principal]

    orden: list[str] = []
    for modelo in [_modelo_fijado] + lista:
        if modelo and modelo not in orden:
            orden.append(modelo)
    return orden


async def generar_sintesis(prompt: str) -> str:
    """
    Envía un prompt a Gemini y retorna el texto generado.
    Prueba el modelo configurado y, si devuelve 404 (obsoleto) o 503/429 (saturado),
    intenta con los modelos de respaldo antes de fallar.
    """
    global _modelo_activo, _modelo_fijado, _clave_rechazada
    cliente = _get_client()
    errores: list[str] = []

    for modelo in _candidatos():
        reintentos = 2
        for intento in range(reintentos):
            try:
                respuesta = await cliente.aio.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,  # más determinista para síntesis científica
                        max_output_tokens=4096,
                    ),
                )
                texto = (respuesta.text or "").strip()
                if texto:
                    _modelo_activo = modelo
                    _modelo_fijado = modelo
                    return texto
                errores.append(f"{modelo}: respuesta vacía")
                _soltar_si_fijado(modelo)
                break
            except Exception as error:  # noqa: BLE001 - se re-intenta con otro modelo
                errores.append(f"{modelo}: {type(error).__name__}: {str(error)[:160]}")
                if _es_fallo_de_clave(error):
                    # Probar otros modelos no sirve: Google rechaza la clave, no el modelo.
                    _clave_rechazada = True
                    logging.getLogger(__name__).error(
                        "Gemini rechazó la API key: %s", str(error)[:200]
                    )
                    raise ClaveGeminiInvalida() from error
                if _es_transitorio(error) and intento + 1 < reintentos:
                    await asyncio.sleep(2.0 * (intento + 1))
                    continue
                _soltar_si_fijado(modelo)
                break

    raise RuntimeError(
        "Gemini no pudo generar la respuesta. " + " | ".join(errores[-3:])
    )


def get_nombre_modelo() -> str:
    """Modelo realmente usado en la última generación (o el configurado)."""
    return _modelo_activo or get_settings().gemini_model
