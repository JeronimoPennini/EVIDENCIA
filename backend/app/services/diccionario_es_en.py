"""
EvidencIA — Diccionario clínico español → inglés (MeSH / PubMed)

Semilla de traducción para el vocabulario controlado. No reemplaza al diccionario
DeCS/MeSH oficial: entrega la frase en inglés que luego `decs_service` valida y
normaliza contra el descriptor MeSH canónico.
"""

import re
import unicodedata

# Diccionario médico de traducción español -> inglés (MeSH / PubMed keywords)
DICCIONARIO_MEDICO = {
    # Enfermedades y poblaciones
    "diabetes tipo 2": "Diabetes Mellitus, Type 2",
    "diabetes mellitus tipo 2": "Diabetes Mellitus, Type 2",
    "diabetes tipo 1": "Diabetes Mellitus, Type 1",
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
    "inhibidores de la sglt2": "Sodium-Glucose Transporter 2 Inhibitors",
    "inhibidores de sglt2": "Sodium-Glucose Transporter 2 Inhibitors",
    "inhibidores sglt2": "Sodium-Glucose Transporter 2 Inhibitors",
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

    # Metodología / tipos de estudio (en español, para uso del usuario)
    "revision sistematica": "systematic review",
    "revisión sistemática": "systematic review",
    "metaanalisis": "meta-analysis",
    "metaanálisis": "meta-analysis",
    "ensayo clinico aleatorizado": "randomized controlled trial",
    "ensayo clínico aleatorizado": "randomized controlled trial",
    "eca": "randomized controlled trial",
    "estudio de cohorte": "cohort study",
    "casos y controles": "case-control study",
    "evaluacion de tecnologias sanitarias": "health technology assessment",
    "evaluación de tecnologías sanitarias": "health technology assessment",
}

STOP_WORDS_ES = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "con", "en", "por",
    "para", "y", "o", "u", "sobre", "del", "al", "a", "ante", "bajo", "desde",
    "hacia", "hasta", "mediante", "sin", "tras", "durante", "segun", "según", "contra",
    "paciente", "pacientes", "adulto", "adultos", "persona", "personas", "poblacion", "población",
    "sujeto", "sujetos", "efecto", "efectos", "reduccion", "reducción", "disminucion", "disminución",
    "mejora", "mejoría", "evaluacion", "evaluación", "resultado", "resultados", "soporte", "grave", "graves",
}

# Términos funcionales que NO deben buscarse como concepto clínico
TERMINOS_NO_CLINICOS = {
    "en", "cual", "efecto", "comparacion", "comparación", "impacto", "influence",
    "versus", "vs", "versus placebo", "estudio", "estudios",
}


def _sin_acentos(texto: str) -> str:
    """Quita tildes: el usuario escribe 'hipertensión' e 'hipertension' y ambos son válidos."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


# Claves normalizadas sin tildes (conserva la última definición encontrada)
DICCIONARIO_SIN_ACENTOS: dict[str, str] = {
    _sin_acentos(k): v for k, v in sorted(DICCIONARIO_MEDICO.items())
}
STOP_WORDS_NORMALIZADAS = {_sin_acentos(w) for w in STOP_WORDS_ES}


def traducir_termino(texto: str) -> str:
    """
    Convierte frases clínicas en español a términos clave en inglés para PubMed,
    reemplazando diccionarios, ajustando sufijos farmacológicos y quitando stop words.
    La búsqueda de claves es insensible a tildes y mayúsculas.
    """
    if not texto:
        return ""

    t = _sin_acentos(texto.lower().strip())
    # Reemplazo de frases compuestas primero (orden descendente de longitud)
    for k, v in sorted(DICCIONARIO_SIN_ACENTOS.items(), key=lambda x: -len(x[0])):
        if k in t:
            t = t.replace(k, f" {v} ")

    palabras: list[str] = []
    for w in t.split():
        w_clean = re.sub(r"[^\w\-]", "", w).strip()
        if not w_clean or _sin_acentos(w_clean.lower()) in STOP_WORDS_NORMALIZADAS:
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
