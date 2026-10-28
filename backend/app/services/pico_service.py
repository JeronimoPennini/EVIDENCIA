"""
EvidencIA — Servicio PICO
Traduce y optimiza preguntas clínicas PICO en queries para PubMed usando el
vocabulario controlado DeCS/MeSH (decs_service) y asistencia de IA (Gemini), y
formula la pregunta clínica estructurada en lenguaje natural.
"""

from typing import Tuple, Optional
import re

from app.models.search import PicoSearchRequest, SearchResponse, TerminoClinico, ArticleResult
from app.services import pubmed_service, gemini_service, decs_service, evidence_service
from app.services.diccionario_es_en import DICCIONARIO_MEDICO, STOP_WORDS_ES, traducir_termino
from app.config import get_settings

# Compatibilidad con llamados antiguos dentro del proyecto
_traducir_y_limpiar_termino = traducir_termino


def construir_pregunta_clinica(
    poblacion: str,
    intervencion: str,
    comparacion: str = "",
    outcome: str = "",
) -> str:
    """Formula la pregunta clínica estructurada en español a partir de PICO."""
    p = poblacion.strip()
    i = intervencion.strip()
    c = comparacion.strip()
    o = outcome.strip()

    comp_str = f" en comparación con {c}" if c else ""
    return f"En {p}, ¿cuál es el efecto de {i}{comp_str} sobre {o}?"


def _aplicar_filtro_estudio(query: str, filtro: str) -> str:
    """Añade filtros metodológicos de evidencia científica a la query."""
    filtro_lower = (filtro or "all").lower().strip()
    if filtro_lower == "rct":
        return f"({query}) AND (randomized controlled trial[Filter] OR clinical trial[Filter])"
    elif filtro_lower in ("systematic_review", "systematic-review", "meta_analysis"):
        return f"({query}) AND (systematic review[Filter] OR meta-analysis[Filter])"
    return query


def construir_query_fallback(
    poblacion: str,
    intervencion: str,
    comparacion: str = "",
    outcome: str = "",
    filtro_estudio: str = "all",
) -> str:
    """
    Construye una query booleana inteligente combinando los términos PICO traducidos
    por el diccionario local. Se usa sin red y sin IA (modo degradado).
    """
    p_en = _traducir_y_limpiar_termino(poblacion) or poblacion.strip()
    i_en = _traducir_y_limpiar_termino(intervencion) or intervencion.strip()
    c_en = _traducir_y_limpiar_termino(comparacion) if comparacion else ""
    o_en = _traducir_y_limpiar_termino(outcome) if outcome else ""

    partes = [f"({p_en})", f"({i_en})"]
    if c_en:
        partes.append(f"({c_en})")
    if o_en:
        partes.append(f"({o_en})")

    query_base = " AND ".join(partes)
    return _aplicar_filtro_estudio(query_base, filtro_estudio)


def _clausuras_por_termino(terminos: list[TerminoClinico]) -> str:
    """Une las cláusuras MeSH/texto libre de cada término con AND."""
    usadas = [t.clausura for t in terminos if t.clausura and t.entrada]
    return " AND ".join(usadas)


async def construir_query_vocabulario(
    poblacion: str,
    intervencion: str,
    comparacion: str = "",
    outcome: str = "",
    filtro_estudio: str = "all",
) -> Tuple[str, list[TerminoClinico]]:
    """
    Resuelve cada componente PICO contra DeCS/MeSH y arma la query booleana.
    Los componentes vacíos (p.ej. C opcional) se resuelven igual para poder mostrarlos.
    """
    entradas = [poblacion, intervencion]
    if comparacion and comparacion.strip():
        entradas.append(comparacion)
    if outcome and outcome.strip():
        entradas.append(outcome)

    terminos = await decs_service.resolver_terminos(entradas)
    query = _clausuras_por_termino(terminos)
    return _aplicar_filtro_estudio(query, filtro_estudio) if query else query, terminos


async def traducir_y_optimizar_pico(
    poblacion: str,
    intervencion: str,
    comparacion: str = "",
    outcome: str = "",
    filtro_estudio: str = "all",
) -> Tuple[str, str]:
    """
    Usa Gemini para traducir los términos clínicos a inglés médico y MeSH,
    generando una query booleana optimizada para PubMed y una pregunta clínica formal.
    Retorna (pregunta_clinica, query_pubmed).
    """
    settings = get_settings()
    pregunta_fallback = construir_pregunta_clinica(poblacion, intervencion, comparacion, outcome)
    query_fallback = construir_query_fallback(
        poblacion, intervencion, comparacion, outcome, filtro_estudio
    )

    if not _gemini_disponible(settings):
        return pregunta_fallback, query_fallback

    prompt = f"""Eres un experto en Medicina Basada en la Evidencia y búsquedas bibliográficas en PubMed / MEDLINE.

A partir de los siguientes componentes PICO ingresados en español:
- P (Población/Paciente/Problema): {poblacion}
- I (Intervención): {intervencion}
- C (Comparación/Control): {comparacion if comparacion else 'No especificado (placebo o control habitual)'}
- O (Desenlace/Outcome): {outcome}

Genera dos elementos:
1. PREGUNTA_CLINICA: Redacta en español la pregunta clínica formal de forma clara y precisa.
2. QUERY_PUBMED: Construye una query booleana válida para la API de PubMed en INGLÉS. Combina P, I y O con AND. Cuando un componente corresponda a un concepto MeSH existente, úsalo como "Descriptor MeSH exacto"[MeSH Terms] escribiendo la etiqueta oficial del descriptor (no un sinónimo inventado); agrega sinónimos en inglés con OR y texto libre [tiab] como respaldo. NO agregues comillas markdown ni explicaciones adicionales.

Ejemplo de formato de salida obligatorio:
PREGUNTA_CLINICA: En pacientes adultos con insuficiencia cardíaca con fracción de eyección preservada, ¿cuál es el efecto de la empagliflozina en comparación con placebo sobre la reducción de hospitalizaciones y mortalidad cardiovascular?
QUERY_PUBMED: ("Heart Failure"[MeSH Terms] AND "preserved ejection fraction"[tiab]) OR "heart failure with preserved ejection fraction"[tiab]) AND ("empagliflozin"[tiab] OR "Sodium-Glucose Transporter 2 Inhibitors"[MeSH Terms]) AND (hospitalization[tiab] OR "mortality"[MeSH Terms])
"""

    try:
        texto = await gemini_service.generar_sintesis(prompt)
        pregunta = pregunta_fallback
        query = query_fallback

        for linea in texto.strip().splitlines():
            linea = linea.strip()
            if linea.upper().startswith("PREGUNTA_CLINICA:"):
                pregunta = linea.split(":", 1)[1].strip()
            elif linea.upper().startswith("QUERY_PUBMED:"):
                query_candidate = linea.split(":", 1)[1].strip()
                query_candidate = query_candidate.strip("`").strip()
                if query_candidate:
                    query = query_candidate

        # El modelo suele inventar etiquetas MeSH: se reparan contra el vocabulario real.
        if "[MeSH" in query.upper():
            query, _ = await decs_service.reparar_query(query)

        query_final = _aplicar_filtro_estudio(query, filtro_estudio)
        return pregunta, query_final
    except Exception:
        return pregunta_fallback, query_fallback


def _gemini_disponible(settings) -> bool:
    """True si hay una clave Gemini real configurada."""
    clave = (settings.gemini_api_key or "").strip()
    return bool(clave) and not clave.startswith("tu_clave")


def _respuesta_vacia(query: str, pregunta: str) -> SearchResponse:
    return SearchResponse(
        query=query, total_encontrados=0, articulos=[], pregunta_clinica=pregunta
    )


async def procesar_busqueda_pico(request: PicoSearchRequest) -> SearchResponse:
    """
    Orquesta la búsqueda a partir de una pregunta PICO:

    1. Optimiza la query con IA (si hay clave Gemini) y la repara contra DeCS/MeSH.
    2. Arma además la query del vocabulario controlado como respaldo determinista.
    3. Busca priorizando jerarquía de evidencia (ETS > RS/MA > ECA > observacionales)
       o por relevancia simple, según `priorizar_calidad`.
    4. Si no hay resultados, relaja progresivamente: P+I sin desenlace, luego sin filtro
       metodológico, luego cae a la query del diccionario.
    """
    settings = get_settings()
    usado_ia = False
    pregunta = construir_pregunta_clinica(
        request.poblacion, request.intervencion, request.comparacion or "", request.outcome
    )
    query = construir_query_fallback(
        request.poblacion,
        request.intervencion,
        request.comparacion or "",
        request.outcome,
        request.filtro_estudio or "all",
    )
    terminos: list[TerminoClinico] = []
    correcciones: list[str] = []

    # 1) IA (opcional)
    if request.optimizar_con_ia and _gemini_disponible(settings):
        pregunta_ia, query_ia = await traducir_y_optimizar_pico(
            poblacion=request.poblacion,
            intervencion=request.intervencion,
            comparacion=request.comparacion or "",
            outcome=request.outcome,
            filtro_estudio=request.filtro_estudio or "all",
        )
        if query_ia and query_ia != query:
            pregunta, query = pregunta_ia, query_ia
            usado_ia = True

    # 2) Vocabulario controlado DeCS/MeSH
    if request.usar_vocabulario_controlado:
        try:
            query_vocab, terminos = await construir_query_vocabulario(
                request.poblacion,
                request.intervencion,
                request.comparacion or "",
                request.outcome,
                request.filtro_estudio or "all",
            )
            if not usado_ia and query_vocab:
                query = query_vocab
            query, correcciones = await decs_service.reparar_query(query)
        except Exception:
            # Sin vocabulario no se detiene la búsqueda: sigue con el diccionario local
            terminos = []

    niveles = evidence_service.normalizar_niveles(request.niveles)

    # 3) Búsqueda priorizando jerarquía de evidencia
    resultados: list[ArticleResult] = []
    totales_por_nivel: dict[str, int] = {}
    total = 0
    prioridad = False

    if request.priorizar_calidad:
        try:
            busqueda = await pubmed_service.buscar_por_niveles(
                query_base=query,
                niveles=niveles,
                max_results=request.max_results,
                date_from=request.date_from,
                date_to=request.date_to,
            )
            resultados = busqueda["articulos"]
            totales_por_nivel = busqueda["totales_por_nivel"]
            total = busqueda["total_base"]
            prioridad = bool(resultados)
        except Exception:
            resultados = []

    if not resultados:
        resultado = await pubmed_service.buscar_articulos(
            query=query,
            max_results=request.max_results,
            date_from=request.date_from,
            date_to=request.date_to,
        )
        resultados = resultado.articulos
        total = resultado.total_encontrados

    # 4) Relajación progresiva: la descripción larga del desenlace o la población suele
    #    dejar la búsqueda en 0; se reintenta con P+I y luego sin filtro metodológico.
    if total == 0 and not resultados:
        p_clean = _traducir_y_limpiar_termino(request.poblacion) or request.poblacion.strip()
        i_clean = _traducir_y_limpiar_termino(request.intervencion) or request.intervencion.strip()

        query_relajada = _aplicar_filtro_estudio(
            f"({p_clean}) AND ({i_clean})", request.filtro_estudio or "all"
        )
        relax = await pubmed_service.buscar_articulos(
            query=query_relajada,
            max_results=request.max_results,
            date_from=request.date_from,
            date_to=request.date_to,
        )
        if relax.total_encontrados > 0:
            return _armar_respuesta(
                query_relajada, relax, pregunta, usado_ia, terminos, correcciones,
                niveles, prioridad,
            )

        if (request.filtro_estudio or "all") != "all":
            query_sin_filtro = f"({p_clean}) AND ({i_clean})"
            amplio = await pubmed_service.buscar_articulos(
                query=query_sin_filtro,
                max_results=request.max_results,
                date_from=request.date_from,
                date_to=request.date_to,
            )
            if amplio.total_encontrados > 0:
                return _armar_respuesta(
                    query_sin_filtro, amplio, pregunta, usado_ia, terminos, correcciones,
                    niveles, False,
                )

    return _armar_respuesta(
        query, None, pregunta, usado_ia, terminos, correcciones, niveles, prioridad,
        articulos=resultados, total=total, totales_por_nivel=totales_por_nivel,
    )


def _armar_respuesta(
    query: str,
    resultado: Optional[SearchResponse],
    pregunta: str,
    usado_ia: bool,
    terminos: list[TerminoClinico],
    correcciones: list[str],
    niveles: list[str],
    prioridad: bool,
    articulos: Optional[list[ArticleResult]] = None,
    total: Optional[int] = None,
    totales_por_nivel: Optional[dict[str, int]] = None,
) -> SearchResponse:
    """Ensobla la respuesta con la trazabilidad de vocabulario y niveles."""
    items = articulos if articulos is not None else (resultado.articulos if resultado else [])
    conteo_total = total if total is not None else (resultado.total_encontrados if resultado else 0)
    distribucion = evidence_service.resumen_por_nivel(items)
    return SearchResponse(
        query=query,
        total_encontrados=conteo_total,
        articulos=items,
        pregunta_clinica=pregunta,
        query_pubmed=query,
        usado_ia=usado_ia,
        terminos_clinicos=terminos,
        correcciones_vocabulario=correcciones,
        niveles_consultados=niveles if prioridad else [],
        totales_por_nivel=totales_por_nivel or {},
        distribucion_devueltos=distribucion,
        prioridad_calidad=prioridad,
    )
