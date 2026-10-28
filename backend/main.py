"""
EvidencIA — Punto de entrada FastAPI
Configura la aplicación, CORS, routers y el endpoint de salud.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import search, synthesis

settings = get_settings()

app = FastAPI(
    title="EvidencIA API",
    description=(
        "Backend de síntesis de evidencia científica en salud asistida por IA. "
        "Utiliza NCBI PubMed E-utilities y Google Gemini API."
    ),
    version="0.1.0",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc
)

# CORS — permite que Flutter web se comunique con el backend.
# En local alcanza con la regex de localhost (cualquier puerto efímero de
# `flutter run -d chrome`). En producción se agrega el dominio público del
# frontend en ALLOWED_ORIGINS.
_origenes = settings.origins_list
_origenes_abiertos = settings.origins_abiertos
if _origenes_abiertos:
    _origenes = [o for o in _origenes if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origenes,
    allow_origin_regex=(settings.cors_origin_regex or None)
    if not _origenes_abiertos
    else r".*",
    # Con '*' los navegadores descartan una respuesta que declare credenciales.
    allow_credentials=not _origenes_abiertos,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(search.router)
app.include_router(synthesis.router)


@app.get("/health", tags=["Sistema"], summary="Estado del servicio")
async def health_check():
    """Verifica que el backend está activo y muestra la configuración activa."""
    from app.services import decs_service
    from app.services.pico_service import _gemini_disponible

    return {
        "status": "ok",
        "version": "0.1.0",
        "servicio": "EvidencIA API",
        "gemini_configurado": _gemini_disponible(settings),
        "ncbi_api_key_configurada": bool(
            (settings.ncbi_api_key or "").strip()
        ) and not settings.ncbi_api_key.startswith("tu_clave"),
        "modelo_ia": settings.gemini_model,
        "vocabulario": await decs_service.estado_vocabulario(),
        # Diagnóstico de despliegue: confirma que el origen público está autorizado.
        "cors_origenes": settings.origins_list,
        "cors_abierto": settings.origins_abiertos,
        "cors_regex": bool(settings.cors_origin_regex),
    }
