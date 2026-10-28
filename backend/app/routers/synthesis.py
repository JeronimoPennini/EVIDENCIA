"""
EvidencIA — Router de síntesis
Endpoint: POST /api/v1/synthesize
"""

import logging

from fastapi import APIRouter, HTTPException
from app.errors import resumen_error
from app.models.synthesis import SynthesisRequest, SynthesisResponse
from app.services import synthesis_service

logger = logging.getLogger("evidencia.sintesis")

router = APIRouter(prefix="/api/v1", tags=["Síntesis IA"])


@router.post(
    "/synthesize",
    response_model=SynthesisResponse,
    summary="Sintetizar evidencia con IA",
)
async def sintetizar(request: SynthesisRequest) -> SynthesisResponse:
    """
    Sintetiza la evidencia de los artículos seleccionados usando Gemini IA.

    - **pmids**: lista de PubMed IDs a sintetizar (mín. 1)
    - **pregunta_clinica**: pregunta o hipótesis a responder (mín. 10 caracteres)
    - **idioma_respuesta**: 'es' (español) o 'en' (inglés)
    """
    try:
        resultado = await synthesis_service.sintetizar(request)
        return resultado
    except ValueError as e:
        # Mensajes propios de validación: no contienen URLs ni secretos.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Fallo la síntesis")
        raise HTTPException(status_code=502, detail=resumen_error(e))
