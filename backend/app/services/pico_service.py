"""
EvidencIA — Servicio PICO
Traduce y optimiza preguntas clínicas PICO en queries para PubMed y formula
la pregunta clínica estructurada en lenguaje natural.
"""

from typing import Tuple, Optional
import re
from app.models.search import PicoSearchRequest, SearchResponse
from app.services import pubmed_service, gemini_service
from app.config import get_settings


# Diccionario médico de traducción español -> inglés (MeSH / PubMed keywords)
DICCIONARIO_MEDICO = {
    # Enfermedades y poblaciones
    "diabetes tipo 2": "type 2 diabetes",
    "diabetes mellitus tipo 2": "type 2 diabetes mellitus",
    "diabetes tipo 1": "type 1 diabetes",
    "diabetes": "diabetes",
    "insuficiencia cardiaca con fraccion de eyeccion preservada": "heart failure with preserved ejection fraction",
    "insuficiencia cardíaca con fracción de eyección preservada": "heart failure with preserved ejection fraction",
    "insuficiencia cardiaca con fraccion de eyeccion reducida": "heart failure with reduced ejection fraction",
    "insuficiencia cardíaca con fracción de eyección reducida": "heart failure with reduced ejection fraction",
    "insuficiencia cardiaca": "heart failure",
    "insuficiencia cardíaca": "heart failure",
    "falla cardiaca": "heart failure",
    "falla cardíaca": "heart failure",
    "fraccion de eyeccion preservada": "preserved ejection fraction",
    "fracción de eyección preservada": "preserved ejection fraction",
    "fraccion de eyeccion reducida": "reduced ejection fraction",
    "fracción de eyección reducida": "reduced ejection fraction",
    "enfermedad cardiovascular": "cardiovascular disease",
    "enfermedad renal cronica": "chronic kidney disease",
    "enfermedad renal crónica": "chronic kidney disease",
    "enfermedad pulmonar obstructiva cronica": "chronic obstructive pulmonary disease",
    "enfermedad pulmonar obstructiva crónica": "COPD",
    "hipertension arterial": "hypertension",
    "hipertension": "hypertension",
    "hipertensión": "hypertension",
    "fibrilacion auricular no valvular": "nonvalvular atrial fibrillation",
    "fibrilación auricular no valvular": "nonvalvular atrial fibrillation",
    "fibrilacion auricular": "atrial fibrillation",
    "fibrilación auricular": "atrial fibrillation",
    "accidente cerebrovascular": "stroke",
    "acv": "stroke",
    "infarto de miocardio": "myocardial infarction",
    "infarto agudo de miocardio": "acute myocardial infarction",
    "sindrome coronario agudo": "acute coronary syndrome",
    "asma grave": "severe asthma",
    "asma leve": "mild asthma",
    "asma": "asthma",
    "epoc": "COPD",
    "covid-19 grave": "severe COVID-19",
    "covid-19": "COVID-19",
    "coronavirus": "coronavirus",
    "soporte de oxigeno": "oxygen therapy",
    "soporte de oxígeno": "oxygen therapy",
    "ventilacion mecanica": "mechanical ventilation",
    "ventilación mecánica": "mechanical ventilation",
    "cancer": "cancer",
    "cáncer": "cancer",
    "adultos mayores": "elderly",
    "ancianos": "aged",
    "pacientes hospitalizados": "hospitalized patients",
    "hospitalizados": "hospitalized",
    "pediatricos": "pediatric",
    "pediátricos": "pediatric",

    # Fármacos y clases
    "anticoagulantes orales directos": "direct oral anticoagulants",
    "anticoagulantes orales": "oral anticoagulants",
    "anticoagulantes": "anticoagulants",
    "inhibidores de la sglt2": "SGLT2 inhibitors",
    "inhibidores de sglt2": "SGLT2 inhibitors",
    "inhibidores sglt2": "SGLT2 inhibitors",
    "inhibidores ieca": "ACE inhibitors",
    "ieca": "ACE inhibitors",
    "ara-ii": "angiotensin receptor blockers",
    "ara ii": "angiotensin receptor blockers",
    "estatinas": "statins",
    "corticoides": "corticosteroids",
    "corticosteroides": "corticosteroids",
    "placebo": "placebo",
    "cuidado habitual estandar": "standard care",
    "cuidado habitual estándar": "standard care",
    "cuidado habitual": "standard care",
    "cuidado estandar": "standard care",
    "cuidado estándar": "standard care",
    "tratamiento estandar": "standard therapy",
    "tratamiento estándar": "standard therapy",
    "terapia estandar": "standard therapy",

    # Fármacos individuales (sufijos y específicos)
    "empagliflozina": "empagliflozin",
    "dapagliflozina": "dapagliflozin",
    "canagliflozina": "canagliflozin",
    "metformina": "metformin",
    "dexametasona": "dexamethasone",
    "hidrocortisona": "hydrocortisone",
    "losartan": "losartan",
    "losartán": "losartan",
    "enalapril": "enalapril",
    "atorvastatina": "atorvastatin",
    "rosuvastatina": "rosuvastatin",
    "aspirina": "aspirin",
    "warfarina": "warfarin",
    "apixaban": "apixaban",
    "apixabán": "apixaban",
    "rivaroxaban": "rivaroxaban",
    "rivaroxabán": "rivaroxaban",
    "dabigatran": "dabigatran",
    "dabigatrán": "dabigatran",
    "insulina": "insulin",
    "semaglutida": "semaglutide",
    "liraglutida": "liraglutide",
    "budesonida": "budesonide",
    "salbutamol": "salbutamol",

    # Desenlaces / Outcomes
    "mortalidad cardiovascular": "cardiovascular mortality",
    "mortalidad por todas las causas": "all-cause mortality",
    "mortalidad a los 28 dias": "28-day mortality",
    "mortalidad a los 28 días": "28-day mortality",
    "mortalidad": "mortality",
    "muerte": "mortality",
    "hospitalizaciones por insuficiencia cardiaca": "heart failure hospitalization",
    "hospitalizaciones por insuficiencia cardíaca": "heart failure hospitalization",
    "hospitalizaciones": "hospitalization",
    "hospitalizacion": "hospitalization",
    "hospitalización": "hospitalization",
    "ingreso hospitalario": "hospital admission",
    "hemorragia mayor": "major bleeding",
    "sangrado mayor": "major bleeding",
    "sangrado": "bleeding",
    "hemorragia": "hemorrhage",
    "presion arterial": "blood pressure",
    "presión arterial": "blood pressure",
    "crisis asmaticas": "asthma exacerbation",
    "crisis asmáticas": "asthma exacerbation",
    "exacerbaciones": "exacerbations",
    "calidad de vida": "quality of life",
    "eventos adversos": "adverse events",
    "seguridad": "safety",
    "eficacia": "efficacy",
    "supervivencia global": "overall survival",
    "supervivencia": "survival",
}

STOP_WORDS_ES = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "con", "en", "por",
    "para", "y", "o", "u", "sobre", "del", "al", "a", "ante", "bajo", "desde",
    "hacia", "hasta", "mediante", "sin", "tras", "durante", "segun", "según", "contra",
    "paciente", "pacientes", "adulto", "adultos", "persona", "personas", "poblacion", "población",
    "sujeto", "sujetos", "efecto", "efectos", "reduccion", "reducción", "disminucion", "disminución",
    "mejora", "mejoría", "evaluacion", "evaluación", "resultado", "resultados", "soporte", "grave", "graves"
}


def _traducir_y_limpiar_termino(texto: str) -> str:
    """
    Convierte frases clínicas en español a términos clave en inglés para PubMed,
    reemplazando diccionarios, ajustando sufijos farmacológicos y quitando stop words.
    """
    if not texto:
        return ""

    t = texto.lower().strip()
    # Reemplazo de frases compuestas primero (orden descendente de longitud)
    for k, v in sorted(DICCIONARIO_MEDICO.items(), key=lambda x: -len(x[0])):
        if k in t:
            t = t.replace(k, f" {v} ")

    palabras: list[str] = []
    for w in t.split():
        w_clean = re.sub(r"[^\w\-]", "", w).strip()
        if not w_clean or w_clean in STOP_WORDS_ES:
            continue
        # Reglas morfológicas para fármacos comunes
        if w_clean.endswith("ozina") and len(w_clean) > 5:
            w_clean = w_clean[:-5] + "ozin"
        elif w_clean.endswith("ina") and len(w_clean) > 4:
            w_clean = w_clean[:-3] + "in"
        elif w_clean.endswith("ona") and len(w_clean) > 4:
            w_clean = w_clean[:-3] + "one"

        palabras.append(w_clean)

    return " ".join(palabras).strip()


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
    Construye una query booleana inteligente combinando los términos PICO traducidos.
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

    if not settings.gemini_api_key or settings.gemini_api_key.startswith("tu_clave"):
        return pregunta_fallback, query_fallback

    prompt = f"""Eres un experto en Medicina Basada en la Evidencia y búsquedas bibliográficas en PubMed / MEDLINE.

A partir de los siguientes componentes PICO ingresados en español:
- P (Población/Paciente/Problema): {poblacion}
- I (Intervención): {intervencion}
- C (Comparación/Control): {comparacion if comparacion else 'No especificado (placebo o control habitual)'}
- O (Desenlace/Outcome): {outcome}

Genera dos elementos:
1. PREGUNTA_CLINICA: Redacta en español la pregunta clínica formal de forma clara y precisa.
2. QUERY_PUBMED: Construye una query booleana válida para la API de PubMed en INGLÉS. Usa términos en inglés, sinónimos médicos comunes entre paréntesis con OR, y combina P, I y O con AND. NO agregues comillas markdown ni explicaciones adicionales.

Ejemplo de formato de salida obligatorio:
PREGUNTA_CLINICA: En pacientes adultos con insuficiencia cardíaca con fracción de eyección preservada, ¿cuál es el efecto de la empagliflozina en comparación con placebo sobre la reducción de hospitalizaciones y mortalidad cardiovascular?
QUERY_PUBMED: ("heart failure with preserved ejection fraction" OR "HFpEF") AND ("empagliflozin" OR "SGLT2 inhibitors") AND ("hospitalization" OR "mortality")
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

        query_final = _aplicar_filtro_estudio(query, filtro_estudio)
        return pregunta, query_final
    except Exception:
        return pregunta_fallback, query_fallback


async def procesar_busqueda_pico(request: PicoSearchRequest) -> SearchResponse:
    """
    Orquesta la búsqueda a partir de una pregunta PICO:
    1. Traduce u optimiza la query (con IA si está habilitado o con fallback inteligente).
    2. Ejecuta la búsqueda en PubMed.
    3. Si la búsqueda inicial devuelve 0 resultados, aplica relajación progresiva
       (por ejemplo, buscando Población + Intervención sin sobre-restringir en el desenlace).
    4. Retorna los resultados con la pregunta clínica asociada.
    """
    usado_ia = False
    if request.optimizar_con_ia:
        pregunta, query = await traducir_y_optimizar_pico(
            poblacion=request.poblacion,
            intervencion=request.intervencion,
            comparacion=request.comparacion or "",
            outcome=request.outcome,
            filtro_estudio=request.filtro_estudio or "all",
        )
        settings = get_settings()
        if settings.gemini_api_key and not settings.gemini_api_key.startswith("tu_clave"):
            usado_ia = True
    else:
        pregunta = construir_pregunta_clinica(
            poblacion=request.poblacion,
            intervencion=request.intervencion,
            comparacion=request.comparacion or "",
            outcome=request.outcome,
        )
        query = construir_query_fallback(
            poblacion=request.poblacion,
            intervencion=request.intervencion,
            comparacion=request.comparacion or "",
            outcome=request.outcome,
            filtro_estudio=request.filtro_estudio or "all",
        )

    # Consulta inicial a PubMed
    resultado = await pubmed_service.buscar_articulos(
        query=query,
        max_results=request.max_results,
        date_from=request.date_from,
        date_to=request.date_to,
    )

    # Relajación progresiva de búsqueda si no hubo resultados:
    # A menudo PubMed devuelve 0 si la descripción del Outcome o la Población tiene demasiadas palabras
    if resultado.total_encontrados == 0:
        p_clean = _traducir_y_limpiar_termino(request.poblacion) or request.poblacion.strip()
        i_clean = _traducir_y_limpiar_termino(request.intervencion) or request.intervencion.strip()

        # Intento 1: Solo Población + Intervención con filtro de estudio
        query_relajada = _aplicar_filtro_estudio(f"({p_clean}) AND ({i_clean})", request.filtro_estudio or "all")
        resultado_relax = await pubmed_service.buscar_articulos(
            query=query_relajada,
            max_results=request.max_results,
            date_from=request.date_from,
            date_to=request.date_to,
        )

        if resultado_relax.total_encontrados > 0:
            return SearchResponse(
                query=resultado_relax.query,
                total_encontrados=resultado_relax.total_encontrados,
                articulos=resultado_relax.articulos,
                pregunta_clinica=pregunta,
                query_pubmed=query_relajada,
                usado_ia=usado_ia,
            )

        # Intento 2: Si aún da 0 y había filtro RCT/SR, buscar sin filtro metodológico
        if (request.filtro_estudio or "all") != "all":
            query_sin_filtro = f"({p_clean}) AND ({i_clean})"
            resultado_amplio = await pubmed_service.buscar_articulos(
                query=query_sin_filtro,
                max_results=request.max_results,
                date_from=request.date_from,
                date_to=request.date_to,
            )
            if resultado_amplio.total_encontrados > 0:
                return SearchResponse(
                    query=resultado_amplio.query,
                    total_encontrados=resultado_amplio.total_encontrados,
                    articulos=resultado_amplio.articulos,
                    pregunta_clinica=pregunta,
                    query_pubmed=query_sin_filtro,
                    usado_ia=usado_ia,
                )

    return SearchResponse(
        query=resultado.query,
        total_encontrados=resultado.total_encontrados,
        articulos=resultado.articulos,
        pregunta_clinica=pregunta,
        query_pubmed=query,
        usado_ia=usado_ia,
    )
