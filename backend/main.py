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

# CORS — permite que Flutter web se comunique con el backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(search.router)
app.include_router(synthesis.router)


@app.get("/health", tags=["Sistema"], summary="Estado del servicio")
async def health_check():
    """Verifica que el backend está activo y muestra la configuración activa."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "servicio": "EvidencIA API",
        "gemini_configurado": bool(settings.gemini_api_key),
        "ncbi_api_key_configurada": bool(settings.ncbi_api_key),
        "modelo_ia": settings.gemini_model,
    }
