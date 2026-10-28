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
_MODELOS_RESPALDO = ("gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash")

# Códigos que conviene reintentar antes de pasar al siguiente modelo.
_TRANSITORIOS = ("503", "429", "unavailable", "resource_exhausted", "high demand", "timeout")

# Modelo que respondió por última vez (para reportarlo en la respuesta).
_modelo_activo: str = ""


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


def _candidatos() -> list[str]:
    """Modelo configurado primero, luego los respaldos sin duplicar."""
    principal = (get_settings().gemini_model or "gemini-3.5-flash").strip()
    orden = [principal] + [m for m in _MODELOS_RESPALDO if m != principal]
    return orden


async def generar_sintesis(prompt: str) -> str:
    """
    Envía un prompt a Gemini y retorna el texto generado.
    Prueba el modelo configurado y, si devuelve 404 (obsoleto) o 503/429 (saturado),
    intenta con los modelos de respaldo antes de fallar.
    """
    global _modelo_activo
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
                    return texto
                errores.append(f"{modelo}: respuesta vacía")
                break
            except Exception as error:  # noqa: BLE001 - se re-intenta con otro modelo
                errores.append(f"{modelo}: {type(error).__name__}: {str(error)[:160]}")
                if _es_transitorio(error) and intento + 1 < reintentos:
                    await asyncio.sleep(2.0 * (intento + 1))
                    continue
                break

    raise RuntimeError(
        "Gemini no pudo generar la respuesta. " + " | ".join(errores[-3:])
    )


def get_nombre_modelo() -> str:
    """Modelo realmente usado en la última generación (o el configurado)."""
    return _modelo_activo or get_settings().gemini_model
