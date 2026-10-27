"""
EvidencIA — Servicio Gemini IA
Wrapper sobre el SDK google-genai para comunicarse con Gemini API (capa gratuita).
SDK de referencia: https://github.com/googleapis/python-genai
Las claves API se leen exclusivamente desde la configuración del backend.
"""

from google import genai
from google.genai import types
from app.config import get_settings


def _get_client() -> genai.Client:
    """Crea y retorna el cliente Gemini configurado con la API key del backend."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY no configurada. "
            "Obtené tu clave gratuita en https://aistudio.google.com/app/apikey "
            "y agregala al archivo .env"
        )
    return genai.Client(api_key=settings.gemini_api_key)


async def generar_sintesis(prompt: str) -> str:
    """
    Envía un prompt a Gemini y retorna el texto generado.
    Usa la API async nativa del SDK google-genai.
    """
    settings = get_settings()
    client = _get_client()

    respuesta = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,   # más determinista para síntesis científica
            max_output_tokens=4096,
        ),
    )
    return respuesta.text


def get_nombre_modelo() -> str:
    """Retorna el nombre del modelo IA configurado."""
    return get_settings().gemini_model
