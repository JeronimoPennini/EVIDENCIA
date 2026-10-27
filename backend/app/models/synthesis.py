"""
EvidencIA — Modelos de síntesis (Pydantic)
Define los esquemas de entrada/salida para el endpoint de síntesis IA.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SynthesisRequest(BaseModel):
    """Parámetros para sintetizar evidencia de artículos seleccionados."""

    pmids: list[str] = Field(..., min_length=1, description="Lista de PMIDs a sintetizar")
    pregunta_clinica: str = Field(
        ...,
        min_length=10,
        description="Pregunta clínica o hipótesis a responder con la evidencia",
    )
    idioma_respuesta: str = Field(default="es", description="Idioma de la síntesis: 'es' o 'en'")


class Referencia(BaseModel):
    pmid: str
    titulo: str
    autores: str
    año: Optional[int] = None


class SynthesisResponse(BaseModel):
    """Respuesta del motor de síntesis IA."""

    pregunta: str
    sintesis: str = Field(..., description="Síntesis en formato Markdown")
    referencias: list[Referencia] = []
    modelo_ia: str
    advertencia: Optional[str] = Field(
        default="Esta síntesis es generada por IA y no reemplaza el juicio clínico profesional.",
        description="Aviso ético obligatorio",
    )
