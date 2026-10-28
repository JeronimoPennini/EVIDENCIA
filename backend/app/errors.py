"""
EvidencIA — Resumen de errores para respuestas HTTP

`str(e)` de httpx incluye la URL completa del request, y esa URL lleva
`api_key=...`. En una API pública eso es una filtración de credenciales, así que
al cliente sólo le devolvemos un mensaje útil y el detalle se registra en el log
del servidor (Render → Logs).
"""

import httpx


def resumen_error(exc: Exception) -> str:
    """Descripción segura (sin URLs ni secretos) de una excepción de upstream."""
    if isinstance(exc, httpx.HTTPStatusError):
        codigo = exc.response.status_code if exc.response is not None else "?"
        servicio = _nombre_servicio(exc.request.url.host if exc.request is not None else "")
        return (
            f"{servicio} respondió HTTP {codigo}. "
            "Revisá las variables del backend (NCBI_API_KEY, NCBI_EMAIL, DECS_API_KEY, "
            "GEMINI_API_KEY); el detalle está en los logs del servidor."
        )
    if isinstance(exc, httpx.RequestError):
        return (
            "No se pudo contactar a la fuente externa "
            f"({type(exc).__name__}): problema de red o tiempo de espera."
        )
    return f"{type(exc).__name__}: {_primera_linea(exc)}".strip()


def _nombre_servicio(host: str) -> str:
    if "ncbi" in host or "eutils" in host:
        return "NCBI PubMed"
    if "bvsalud" in host:
        return "DeCS (BIREME)"
    if "googleapis" in host or "generativelanguage" in host:
        return "Gemini"
    return "El servicio externo"


def _primera_linea(exc: Exception) -> str:
    """Primera línea del mensaje, recortada y sin query strings."""
    texto = str(exc).strip().splitlines()
    linea = texto[0] if texto else ""
    for separador in ("?", " for url"):
        if separador in linea:
            linea = linea.split(separador)[0]
    return linea[:180]
