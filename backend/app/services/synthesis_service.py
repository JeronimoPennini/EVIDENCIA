"""
EvidencIA — Motor de Síntesis
Orquesta: recupera artículos desde PubMed, construye el prompt y solicita síntesis a Gemini.
"""

from typing import Optional

from app.models.synthesis import SynthesisRequest, SynthesisResponse, Referencia
from app.services import pubmed_service, gemini_service, evidence_service

# Límite de caracteres de abstract por artículo para no exceder el contexto del modelo
MAX_ABSTRACT_CHARS = 1500


def _construir_prompt(pregunta: str, articulos_texto: str, idioma: str, distribucion: dict[str, int]) -> str:
    """Construye el prompt estructurado para Gemini."""
    idioma_instruccion = (
        "Responde en español." if idioma == "es" else "Respond in English."
    )
    lineas_niveles = "\n".join(
        f"- {evidence_service.etiqueta_nivel(codigo)}: {cantidad}"
        for codigo, cantidad in distribucion.items()
        if cantidad
    )

    return f"""Eres un asistente de síntesis de evidencia médica. {idioma_instruccion}

Tu tarea es sintetizar la evidencia científica de los siguientes artículos de PubMed para responder la pregunta clínica planteada.
Los artículos ya están agrupados y ordenados por jerarquía de evidencia de calidad:

**Distribución de la evidencia seleccionada:**
{lineas_niveles or "- sin clasificación disponible"}

**Jerarquía (de mayor a menor calidad):**
1. Informes de Evaluación de Tecnologías Sanitarias (ETS/HTA)
2. Revisiones sistemáticas y metaanálisis
3. Ensayos clínicos aleatorizados (ECA)
4. Estudios observacionales de cohorte o de casos y controles
5. Otros diseños

**Instrucciones:**
- Prioriza las conclusiones de los niveles 1 y 2; usá los niveles 3 y 4 para confirmar, matizar o cubrir vacíos.
- Si un resultado sólo aparece en estudios observacionales, decilo explícitamente y marcá el riesgo de confusión.
- No inventes información que no esté en los abstracts, ni valores (OR, RR, IC, NNT) que no aparezcan allí.
- Indicá el nivel de evidencia junto a cada hallazgo principal, citando el PMID.
- Identifica convergencias y divergencias entre niveles de evidencia.
- Abrí la respuesta con un apartado "Conclusión según la mejor evidencia disponible" y usá formato Markdown con secciones claras.
- Incluí al final una sección "Limitaciones de esta síntesis" que mencione la falta de texto completo, el sesgo de publicación y que la graduación tipo GRADE requiere lectura humana.

**Pregunta clínica:**
{pregunta}

**Artículos disponibles:**
{articulos_texto}

Genera la síntesis ahora:"""


async def sintetizar(request: SynthesisRequest) -> SynthesisResponse:
    """
    Proceso completo de síntesis:
    1. Recupera artículos desde PubMed por PMID
    2. Clasifica y ordena por jerarquía de evidencia
    3. Construye prompt con los abstracts agrupados por nivel
    4. Solicita síntesis a Gemini
    5. Retorna respuesta estructurada
    """
    # Paso 1: Recuperar artículos
    articulos = await pubmed_service.fetch_por_pmids(request.pmids)

    if not articulos:
        raise ValueError("No se pudieron recuperar los artículos especificados de PubMed.")

    # Paso 2: Ordenar por calidad de evidencia
    ordenados = evidence_service.ordenar_por_calidad(articulos)
    distribucion = evidence_service.resumen_por_nivel(ordenados)

    # Paso 3: Preparar texto de artículos para el prompt, agrupado por nivel
    partes: list[str] = []
    referencias: list[Referencia] = []
    nivel_actual: Optional[str] = None

    for art in ordenados:
        if art.nivel_evidencia != nivel_actual:
            nivel_actual = art.nivel_evidencia
            partes.append(
                f"\n## Nivel {evidence_service.NIVELES[nivel_actual].orden}: "
                f"{evidence_service.NIVELES[nivel_actual].etiqueta}"
            )

        autores_str = (
            ", ".join(a.nombre for a in art.autores[:3])
            + (" et al." if len(art.autores) > 3 else "")
        )
        abstract_truncado = (art.abstract or "Abstract no disponible")[:MAX_ABSTRACT_CHARS]
        diseno = ", ".join(art.tipos_publicacion) if art.tipos_publicacion else "sin tipos de publicación"
        malla = ", ".join(art.mesh_descriptores[:6]) if art.mesh_descriptores else "sin descriptores MeSH indexados"

        partes.append(
            f"### PMID {art.pmid} — {art.titulo}\n"
            f"**Autores:** {autores_str} | **Revista:** {art.revista} | **Año:** {art.año}\n"
            f"**Nivel de evidencia:** {art.nivel_etiqueta} ({art.senal_nivel})\n"
            f"**Tipos de publicación:** {diseno}\n"
            f"**Descriptores MeSH:** {malla}\n\n"
            f"{abstract_truncado}\n"
        )
        referencias.append(
            Referencia(
                pmid=art.pmid,
                titulo=art.titulo,
                autores=autores_str,
                año=art.año,
                nivel_evidencia=art.nivel_evidencia,
                nivel_etiqueta=art.nivel_etiqueta,
                tipos_publicacion=art.tipos_publicacion,
            )
        )

    articulos_texto = "\n---\n".join(partes)

    # Paso 4: Construir prompt y llamar a Gemini
    prompt = _construir_prompt(
        request.pregunta_clinica, articulos_texto, request.idioma_respuesta, distribucion
    )
    sintesis_texto = await gemini_service.generar_sintesis(prompt)

    # Paso 5: Armar respuesta
    return SynthesisResponse(
        pregunta=request.pregunta_clinica,
        sintesis=sintesis_texto,
        referencias=referencias,
        modelo_ia=gemini_service.get_nombre_modelo(),
        distribucion_niveles=distribucion,
    )
