"""
EvidencIA — Modelos de búsqueda (Pydantic)
Define los esquemas de entrada/salida para los endpoints de búsqueda en PubMed.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    """Parámetros para buscar artículos en PubMed."""

    query: str = Field(..., min_length=3, description="Término o pregunta clínica a buscar")
    max_results: int = Field(default=10, ge=1, le=50, description="Número máximo de resultados")
    date_from: Optional[str] = Field(default=None, description="Fecha inicio (YYYY/MM/DD)")
    date_to: Optional[str] = Field(default=None, description="Fecha fin (YYYY/MM/DD)")


class Author(BaseModel):
    nombre: str
    afiliacion: Optional[str] = None


class ArticleResult(BaseModel):
    """Artículo recuperado de PubMed."""

    pmid: str = Field(..., description="PubMed ID único")
    titulo: str
    autores: list[Author] = []
    revista: Optional[str] = None
    año: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url_pubmed: str = ""


class SearchResponse(BaseModel):
    """Respuesta del endpoint de búsqueda."""

    query: str
    total_encontrados: int
    articulos: list[ArticleResult]
    pregunta_clinica: Optional[str] = None
    query_pubmed: Optional[str] = None
    usado_ia: bool = False


class PicoSearchRequest(BaseModel):
    """Parámetros para buscar artículos a partir de una pregunta PICO."""

    poblacion: str = Field(..., min_length=2, description="P: Paciente, Población o Problema")
    intervencion: str = Field(..., min_length=2, description="I: Intervención o exposición")
    comparacion: Optional[str] = Field(default="", description="C: Comparación o control (opcional)")
    outcome: str = Field(..., min_length=2, description="O: Resultado o desenlace clínico")
    filtro_estudio: Optional[str] = Field(
        default="all",
        description="Filtro metodológico: 'all', 'rct' o 'systematic_review'",
    )
    max_results: int = Field(default=10, ge=1, le=50, description="Número máximo de resultados")
    date_from: Optional[str] = Field(default=None, description="Fecha inicio (YYYY/MM/DD)")
    date_to: Optional[str] = Field(default=None, description="Fecha fin (YYYY/MM/DD)")
    optimizar_con_ia: bool = Field(
        default=True,
        description="Usa IA para traducir términos y construir query PubMed enriquecida",
    )
