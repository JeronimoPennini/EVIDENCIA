"""
EvidencIA — Router de búsqueda
Endpoint: POST /api/v1/search
"""

from fastapi import APIRouter, HTTPException
from app.models.search import SearchRequest, SearchResponse, PicoSearchRequest
from app.services import pubmed_service, pico_service

router = APIRouter(prefix="/api/v1", tags=["Búsqueda"])


@router.post("/search", response_model=SearchResponse, summary="Buscar artículos en PubMed")
async def buscar(request: SearchRequest) -> SearchResponse:
    """
    Busca artículos científicos en PubMed usando NCBI E-utilities.

    - **query**: término de búsqueda o pregunta clínica (mín. 3 caracteres)
    - **max_results**: cantidad de resultados (1–50, por defecto 10)
    - **date_from / date_to**: filtros de fecha opcionales (YYYY/MM/DD)
    """
    try:
        resultado = await pubmed_service.buscar_articulos(
            query=request.query,
            max_results=request.max_results,
            date_from=request.date_from,
            date_to=request.date_to,
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al consultar PubMed: {str(e)}")


@router.post(
    "/search/pico",
    response_model=SearchResponse,
    summary="Buscar evidencia científica mediante pregunta PICO",
)
async def buscar_pico(request: PicoSearchRequest) -> SearchResponse:
    """
    Construye la búsqueda en PubMed a partir de los componentes PICO:
    - **poblacion (P)**: Paciente, población o problema
    - **intervencion (I)**: Intervención o factor de estudio
    - **comparacion (C)**: Comparador o grupo control (opcional)
    - **outcome (O)**: Resultado o desenlace clínico
    - **filtro_estudio**: 'all', 'rct' (ensayos clínicos) o 'systematic_review' (revisiones sistemáticas)
    - **optimizar_con_ia**: Traduce a terminología médica en inglés / MeSH si Gemini está activo.
    """
    try:
        return await pico_service.procesar_busqueda_pico(request)
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Error al procesar la búsqueda PICO: {str(e)}"
        )
