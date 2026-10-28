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


class TerminoClinico(BaseModel):
    """Término PICO resuelto contra el vocabulario controlado DeCS / MeSH."""

    entrada: str = Field(..., description="Texto tal como lo escribió el usuario (español o inglés)")
    descriptor: str = Field(default="", description="Descriptor MeSH canónico encontrado (en inglés)")
    mesh_ui: str = Field(default="", description="Número de registro MeSH/DeCS, ej. D003924")
    decs_nombre: str = Field(default="", description="Nombre del descriptor en DeCS (español), si la API DeCS respondió")
    fuente: str = Field(
        default="diccionario",
        description="Cómo se resolvió: 'decs' | 'mesh' | 'diccionario' | 'vacio'",
    )
    clausura: str = Field(default="", description="Cláusula PubMed generada para este término")


class ArticleResult(BaseModel):
    """Artículo recuperado de PubMed, con su nivel de evidencia clasificado."""

    pmid: str = Field(..., description="PubMed ID único")
    titulo: str
    autores: list[Author] = []
    revista: Optional[str] = None
    año: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url_pubmed: str = ""
    revista_iso: str = Field(default="", description="Abreviatura ISO de la revista (p.ej. Health Technol Assess)")
    tipos_publicacion: list[str] = Field(default_factory=list, description="PublicationTypeList del registro PubMed")
    mesh_descriptores: list[str] = Field(default_factory=list, description="Descriptores MeSH indexados en el artículo")
    afiliaciones: str = Field(default="", description="Afilaciones concatenadas (señal de agencia de ETS)")
    nivel_evidencia: str = Field(default="otros", description="Código de nivel: ets | rs_ma | rct | obs | otros")
    nivel_etiqueta: str = Field(default="Otro tipo de estudio", description="Nivel de evidencia legible")
    nivel_orden: int = Field(default=5, description="1 = máxima calidad (ETS) … 5 = otro diseño")
    senal_nivel: str = Field(default="", description="Metadato que justificó la clasificación")
    recuperado_por_nivel: str = Field(default="", description="Nivel consultado que trajo este registro")


class SearchResponse(BaseModel):
    """Respuesta del endpoint de búsqueda."""

    query: str
    total_encontrados: int
    articulos: list[ArticleResult]
    pregunta_clinica: Optional[str] = None
    query_pubmed: Optional[str] = None
    usado_ia: bool = False
    aviso_ia: Optional[str] = Field(
        default=None,
        description="Por qué no se usó IA cuando se pidió (clave inválida, cuota, red).",
    )
    terminos_clinicos: list[TerminoClinico] = Field(
        default_factory=list, description="Términos PICO resueltos contra DeCS/MeSH"
    )
    correcciones_vocabulario: list[str] = Field(
        default_factory=list, description="Descriptores MeSH inválidos detectados y corregidos"
    )
    niveles_consultados: list[str] = Field(default_factory=list, description="Niveles de evidencia buscados")
    totales_por_nivel: dict[str, int] = Field(
        default_factory=dict, description="Artículos disponibles en PubMed por nivel"
    )
    distribucion_devueltos: dict[str, int] = Field(
        default_factory=dict, description="Artículos devueltos por nivel de evidencia"
    )
    prioridad_calidad: bool = Field(default=False, description="Se buscó por niveles en lugar de por relevancia")


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
    usar_vocabulario_controlado: bool = Field(
        default=True,
        description="Resuelve P, I, C y O contra DeCS/MeSH y repara la query PubMed",
    )
    priorizar_calidad: bool = Field(
        default=True,
        description="Busca por niveles de evidencia (ETS > RS/MA > ECA > observacionales) en vez de solo relevancia",
    )
    niveles: Optional[list[str]] = Field(
        default=None,
        description="Subconjunto de niveles a consultar: ets, rs_ma, rct, obs",
    )
