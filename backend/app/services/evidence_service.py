"""
EvidencIA — Jerarquía de evidencia de calidad

Define el orden de prioridad solicitado:

  1. Informes de Evaluación de Tecnologías Sanitarias (ETS / HTA)
  2. Revisiones sistemáticas y metaanálisis
  3. Ensayos clínicos aleatorizados (ECA)
  4. Estudios observacionales de cohorte o de casos y controles
  5. Otros diseños

Las etiquetas de consulta (`CLAUSULAS_NIVEL`) y los tipos de publicación usados están
verificados contra la API de PubMed (2026-10-28). Notas de la verificación:

- `"Cohort Studies"[Publication Type]` y `"Case-Control Studies"[Publication Type]`
  devuelven **0**: hay que usarlos como `[MeSH Terms]` (D015331 y D016022).
- No existe `"Health Technology Assessment"[Publication Type]`, ni descriptor MeSH con ese
  nombre exacto, ni `hta[Filter]`. PubMed no indexa informes ETS como tipo de publicación,
  por eso la detección de ETS es una heurística multiparqueador (descriptor
  "Technology Assessment, Biomedical" D013673 + revistas de agencias + nombre de agencia).
- Toda cláusula de nivel va entre paréntesis: PubMed no aplica precedencia OR sobre AND,
  así que `base AND A OR B` expande B a todo PubMed.
"""

from dataclasses import dataclass
from typing import Iterable, Optional

from app.models.search import ArticleResult


@dataclass(frozen=True)
class Nivel:
    """Puesto en la jerarquía de evidencia y su etiqueta legible."""

    codigo: str
    orden: int
    etiqueta: str
    descripcion: str


NIVELES: dict[str, Nivel] = {
    "ets": Nivel(
        "ets",
        1,
        "Evaluación de Tecnología Sanitaria (ETS/HTA)",
        "Informes de agencias de evaluación de tecnologías sanitarias: la evidencia de mayor calidad metodológica y la que sustenta decisiones de financiamiento.",
    ),
    "rs_ma": Nivel(
        "rs_ma",
        2,
        "Revisión sistemática / Metaanálisis",
        "Síntesis explícita y reproducible de la literatura, incluidos metaanálisis directos y en red.",
    ),
    "rct": Nivel(
        "rct",
        3,
        "Ensayo clínico aleatorizado",
        "Estudio experimental con asignación aleatoria (y ensayos clínicos controlados de fase o pragmáticos).",
    ),
    "obs": Nivel(
        "obs",
        4,
        "Estudio observacional (cohorte / casos y controles)",
        "Diseños analíticos no experimentales: cohortas prospectivas o retrospectivas y casos y controles.",
    ),
    "otros": Nivel(
        "otros",
        5,
        "Otro tipo de estudio",
        "Diseños transversales, series de casos, editoriales, cartas y otros registros sin clasificación metodológica explícita.",
    ),
}

ORDEN_NIVELES: list[str] = ["ets", "rs_ma", "rct", "obs", "otros"]

# --- Tipos de publicación (etiquetas tal como llegan en PublicationTypeList) ---------
PT_RS_MA = {
    "meta-analysis",
    "systematic review",
    "network meta-analysis",
}
PT_RCT = {
    "randomized controlled trial",
    "controlled clinical trial",
    "clinical trial",
    "clinical trial, phase ii",
    "clinical trial, phase iii",
    "clinical trial, phase iv",
    "pragmatic clinical trial",
    "equivalence trial",
    "multicenter study",
    "randomized cross-over trial",
}
# Ensayos donde la aleatorización no está explícita en el tipo de publicación.
PT_RCT_NO_EXPLICITAS = {
    "clinical trial",
    "clinical trial, phase ii",
    "clinical trial, phase iii",
    "clinical trial, phase iv",
    "pragmatic clinical trial",
    "equivalence trial",
    "multicenter study",
    "controlled clinical trial",
}
PT_OBS = {"observational study"}

# --- Descriptores MeSH de diseño ----------------------------------------------------
MESH_OBS_FUERTES = {"cohort studies", "case-control studies", "prospective studies", "retrospective studies"}
MESH_ETS = {"technology assessment, biomedical"}

# --- Revistas de agencias / literatura de ETS ---------------------------------------
REVISTAS_ETS = {
    "health technol assess",
    "int j technol assess health care",
    "value health reg issues",
    "expert rev pharmacoecon outcomes res",
    "appl health econ health policy",
    "pharmacoepidemiol drug saf",
}
SENAL_ECONOMICA = (
    "cost-effectiveness",
    "cost-utility",
    "budget impact",
    "economic evaluation",
    "cost-benefit",
)

# --- Agencias de ETS y frases de informe --------------------------------------------
AGENCIAS_ETS = (
    "nihr",
    "cadth",
    "has-france",
    "haute autorite",
    "ghta",
    "conitec",
    "aetma",
    "agceamev",
    "agcemev",
    "aetsa",
    "aquis",
    "dimas",
    "ipk",
    "eunetchta",
    "inethts",
    "evaluacion de tecnologias",
    "avaliação de tecnologias",
    "agencia de evaluacion",
    "agencia española",
)
FRASES_ETS = (
    "health technology assessment",
    "health technology appraisal",
    "health technology assessments",
    "hta report",
    "hta-report",
    "evidence report",
    "technology assessment report",
    "rapid review for",
    "health technologies assessment",
)

# --- Cláusulas de consulta verificadas en PubMed (siempre parentizadas) --------------
CLAUSULAS_NIVEL: dict[str, str] = {
    "ets": (
        '('
        '"Technology Assessment, Biomedical"[MeSH Terms]'
        ' OR "health technology assessment"[tiab]'
        ' OR "health technology appraisal"[tiab]'
        ' OR "health technology assessments"[tiab]'
        ' OR "Health Technol Assess"[ta]'
        ' OR "Int J Technol Assess Health Care"[ta]'
        ' OR "Value Health Reg Issues"[ta]'
        ')'
    ),
    "rs_ma": (
        '('
        '"Meta-Analysis"[Publication Type]'
        ' OR "Systematic Review"[Publication Type]'
        ' OR "Network Meta-Analysis"[Publication Type]'
        ')'
    ),
    "rct": '("Randomized Controlled Trial"[Publication Type])',
    "obs": (
        '('
        '"Cohort Studies"[MeSH Terms]'
        ' OR "Case-Control Studies"[MeSH Terms]'
        ' OR (Observational Study[Filter])'
        ')'
    ),
    "otros": "",  # sin filtro: se usa como residuo
}

# Peso relativo de cupo por nivel cuando se busca priorizando calidad.
PESOS_NIVEL: dict[str, float] = {"ets": 3.0, "rs_ma": 3.0, "rct": 3.0, "obs": 2.0, "otros": 1.0}


# --------------------------------------------------------------------------- clasificación


def _normal(texto: Optional[str]) -> str:
    return (texto or "").lower().strip()


def _senales_ets(
    mesh: Iterable[str],
    texto_buscado: str,
    revista_iso: str,
    pt_etiquetas: list[str],
) -> list[str]:
    """Lista las señales que indican que un registro es (o contiene) un informe ETS."""
    senales: list[str] = []
    if MESH_ETS & set(mesh):
        senales.append("descriptor MeSH Technology Assessment, Biomedical")
    if any(f in texto_buscado for f in FRASES_ETS):
        senales.append("frase de evaluación de tecnologías sanitarias en título/abstract")
    if any(a in texto_buscado for a in AGENCIAS_ETS):
        senales.append("mención de agencia de ETS")
    if revista_iso in REVISTAS_ETS and any(s in texto_buscado for s in SENAL_ECONOMICA):
        senales.append("revista de ETS con evaluación económica")
    if "health technology assessment" in " ".join(pt_etiquetas):
        senales.append("tipo de publicación de ETS")
    return senales


def clasificar_articulo(
    tipos_publicacion: list[str],
    mesh_descriptores: list[str],
    titulo: str = "",
    abstract: str = "",
    revista_iso: str = "",
    afiliaciones: str = "",
) -> tuple[str, str]:
    """
    Asigna el nivel de evidencia a un registro a partir de su metadato bibliográfico.

    Retorna `(codigo_nivel, senal_detectada)`. Gana siempre el nivel de mayor jerarquía
    cuya señal esté presente; si un artículo es ETS y además ECA, se reporta como ETS.
    """
    pt = [_normal(p) for p in tipos_publicacion]
    pt_exactos = {p for p in pt if p}
    mesh = {_normal(m) for m in mesh_descriptores}
    texto = " ".join([_normal(titulo), _normal(abstract), _normal(afiliaciones)])
    revista = _normal(revista_iso)

    ets = _senales_ets(mesh, texto, revista, pt)
    if ets:
        return "ets", "; ".join(ets)

    if PT_RS_MA & pt_exactos:
        ganadores = sorted(PT_RS_MA & pt_exactos)
        return "rs_ma", f"tipo de publicación: {', '.join(ganadores)}"

    if PT_RCT & pt_exactos:
        if (PT_RCT & pt_exactos) - PT_RCT_NO_EXPLICITAS:
            return "rct", "tipo de publicación: ensayo con aleatorización explícita"
        return "rct", "tipo de publicación: ensayo clínico controlado (aleatorización no explícita)"

    if "observational study" in pt_exactos or (MESH_OBS_FUERTES & mesh):
        detalle = ", ".join(sorted({"observational study"} & pt_exactos | (MESH_OBS_FUERTES & mesh)))
        return "obs", f"diseño observacional: {detalle}"

    return "otros", "sin marcador metodológico explícito en el registro"


def aplicar_clasificacion(articulo: ArticleResult) -> ArticleResult:
    """Escribe nivel, orden, etiqueta y señal detectada sobre el modelo del artículo."""
    codigo, senal = clasificar_articulo(
        tipos_publicacion=articulo.tipos_publicacion,
        mesh_descriptores=articulo.mesh_descriptores,
        titulo=articulo.titulo,
        abstract=articulo.abstract or "",
        revista_iso=articulo.revista_iso,
        afiliaciones=articulo.afiliaciones,
    )
    nivel = NIVELES[codigo]
    articulo.nivel_evidencia = nivel.codigo
    articulo.nivel_etiqueta = nivel.etiqueta
    articulo.nivel_orden = nivel.orden
    articulo.senal_nivel = senal
    return articulo


def ordenar_por_calidad(articulos: list[ArticleResult]) -> list[ArticleResult]:
    """Ordena por jerarquía de evidencia y, dentro del nivel, por año descendente."""
    return sorted(
        articulos,
        key=lambda a: (a.nivel_orden, -(a.año or 0), a.titulo.lower()),
    )


def resumen_por_nivel(articulos: list[ArticleResult]) -> dict[str, int]:
    """Cuenta de artículos devueltos por nivel (incluye los niveles en cero)."""
    conteo = {codigo: 0 for codigo in ORDEN_NIVELES}
    for a in articulos:
        conteo[a.nivel_evidencia if a.nivel_evidencia in conteo else "otros"] += 1
    return conteo


# ----------------------------------------------------------------------- planificación


def normalizar_niveles(solicitados: Optional[list[str]]) -> list[str]:
    """Filtra y ordena los niveles pedidos; si vienen vacíos, usa toda la jerarquía."""
    if not solicitados:
        return [c for c in ORDEN_NIVELES if c != "otros"]
    validos = [c for c in ORDEN_NIVELES if c in set(solicitados)]
    # "otros" nunca se consulta como cláusula: se obtiene por relajación.
    return [c for c in validos if c != "otros"] or [c for c in ORDEN_NIVELES if c != "otros"]


def cotas_por_nivel(max_results: int, niveles: list[str]) -> dict[str, int]:
    """
    Reparte el cupo de resultados entre niveles según PESOS_NIVEL, garantizando al menos
    un hueco por nivel para que los ETS/RS no queden desplazados por el caudal de ECA.
    """
    niveles = [n for n in niveles if n in PESOS_NIVEL]
    if not niveles:
        return {}
    total_peso = sum(PESOS_NIVEL[n] for n in niveles)
    asignacion = {n: max(1, int(round(max_results * PESOS_NIVEL[n] / total_peso))) for n in niveles}

    # Ajuste fino para no superar el máximo pedido.
    excedente = sum(asignacion.values()) - max_results
    for n in sorted(asignacion, key=lambda c: -PESOS_NIVEL[c]):
        if excedente <= 0:
            break
        recorte = min(asignacion[n] - 1, excedente)
        asignacion[n] -= recorte
        excedente -= recorte
    return asignacion


def construir_query_nivel(query_base: str, nivel: str) -> str:
    """Combina la base PICO con la cláusula del nivel (parenizada, sin romper precedencia)."""
    clausula = CLAUSULAS_NIVEL.get(nivel, "")
    if not clausula:
        return query_base
    return f"({query_base.strip()}) AND {clausula}"


def query_para_niveles(query_base: str, niveles: list[str]) -> str:
    """Una sola query que acepta varios niveles de la jerarquía (OR entre cláusulas)."""
    seleccion = normalizar_niveles(niveles)
    partes = [CLAUSULAS_NIVEL[n] for n in seleccion if CLAUSULAS_NIVEL.get(n)]
    if not partes:
        return query_base
    return f"({query_base.strip()}) AND ({' OR '.join(partes)})"


def etiqueta_nivel(codigo: str) -> str:
    """Etiqueta legible para el frontend."""
    nivel = NIVELES.get(codigo)
    return nivel.etiqueta if nivel else NIVELES["otros"].etiqueta
