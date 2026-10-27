"""
EvidencIA — Motor de Síntesis
Orquesta: recupera artículos desde PubMed, construye el prompt y solicita síntesis a Gemini.
"""

from app.models.synthesis import SynthesisRequest, SynthesisResponse, Referencia
from app.services import pubmed_service, gemini_service

# Límite de caracteres de abstract por artículo para no exceder el contexto del modelo
MAX_ABSTRACT_CHARS = 1500


def _construir_prompt(pregunta: str, articulos_texto: str, idioma: str) -> str:
    """Construye el prompt estructurado para Gemini."""
    idioma_instruccion = (
        "Responde en español." if idioma == "es" else "Respond in English."
    )

    return f"""Eres un asistente de síntesis de evidencia médica. {idioma_instruccion}

Tu tarea es sintetizar la evidencia científica de los siguientes artículos de PubMed para responder la pregunta clínica planteada.

**Instrucciones:**
- Resume los hallazgos principales de cada artículo relevante.
- Identifica convergencias y divergencias en la evidencia.
- Señala el nivel de evidencia (si es inferible) y limitaciones importantes.
- Usa formato Markdown con secciones claras.
- Sé preciso y no inventes información que no esté en los abstracts.
- Incluye al final una sección "Limitaciones de esta síntesis".

**Pregunta clínica:**
{pregunta}

**Artículos disponibles:**
{articulos_texto}

Genera la síntesis ahora:"""


async def sintetizar(request: SynthesisRequest) -> SynthesisResponse:
    """
    Proceso completo de síntesis:
    1. Recupera artículos desde PubMed por PMID
    2. Construye prompt con los abstracts
    3. Solicita síntesis a Gemini
    4. Retorna respuesta estructurada
    """
    # Paso 1: Recuperar artículos
    articulos = await pubmed_service.fetch_por_pmids(request.pmids)

    if not articulos:
        raise ValueError("No se pudieron recuperar los artículos especificados de PubMed.")

    # Paso 2: Preparar texto de artículos para el prompt
    partes: list[str] = []
    referencias: list[Referencia] = []

    for art in articulos:
        autores_str = (
            ", ".join(a.nombre for a in art.autores[:3])
            + (" et al." if len(art.autores) > 3 else "")
        )
        abstract_truncado = (art.abstract or "Abstract no disponible")[:MAX_ABSTRACT_CHARS]

        partes.append(
            f"### PMID {art.pmid} — {art.titulo}\n"
            f"**Autores:** {autores_str} | **Revista:** {art.revista} | **Año:** {art.año}\n\n"
            f"{abstract_truncado}\n"
        )
        referencias.append(
            Referencia(
                pmid=art.pmid,
                titulo=art.titulo,
                autores=autores_str,
                año=art.año,
            )
        )

    articulos_texto = "\n---\n".join(partes)

    # Paso 3: Construir prompt y llamar a Gemini
    prompt = _construir_prompt(request.pregunta_clinica, articulos_texto, request.idioma_respuesta)
    sintesis_texto = await gemini_service.generar_sintesis(prompt)

    # Paso 4: Armar respuesta
    return SynthesisResponse(
        pregunta=request.pregunta_clinica,
        sintesis=sintesis_texto,
        referencias=referencias,
        modelo_ia=gemini_service.get_nombre_modelo(),
    )
