"""
EvidencIA — Tests de la jerarquía de evidencia de calidad

Cubren la clasificación por metadatos reales de PubMed (tipos de publicación y
descriptores MeSH), el orden por jerarquía y la construcción de queries por nivel.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from app.models.search import ArticleResult
from app.services import evidence_service

client = TestClient(app)


def _articulo(pmid: str, nivel: str = "", **kwargs) -> ArticleResult:
    art = ArticleResult(
        pmid=pmid,
        titulo=kwargs.get("titulo", f"Artículo {pmid}"),
        revista=kwargs.get("revista"),
        revista_iso=kwargs.get("revista_iso", ""),
        año=kwargs.get("año"),
        abstract=kwargs.get("abstract", ""),
        tipos_publicacion=kwargs.get("tipos_publicacion", []),
        mesh_descriptores=kwargs.get("mesh_descriptores", []),
        afiliaciones=kwargs.get("afiliaciones", ""),
    )
    return evidence_service.aplicar_clasificacion(art)


# ---------------------------------------------------------------------- clasificación


def test_metaanalisis_y_revision_sistematicaSon_nivel_dos():
    for pt in (["Meta-Analysis"], ["Systematic Review"], ["Network Meta-Analysis"]):
        art = _articulo("1", tipos_publicacion=["Journal Article"] + pt)
        assert art.nivel_evidencia == "rs_ma", pt
        assert art.nivel_orden == 2


def test_eca_es_nivel_tres():
    art = _articulo(
        "2",
        tipos_publicacion=["Journal Article", "Randomized Controlled Trial", "Multicenter Study"],
        año=2025,
    )
    assert art.nivel_evidencia == "rct"
    assert "aleatorización explícita" in art.senal_nivel


def test_ensayo_de_fase_sin_aleatorizacion_explita_se_advierte():
    art = _articulo("3", tipos_publicacion=["Clinical Trial, Phase III"])
    assert art.nivel_evidencia == "rct"
    assert "no explícita" in art.senal_nivel


def test_cohorte_y_casos_y_controles_son_nivel_cuatro():
    cohorte = _articulo("4", mesh_descriptores=["Cohort Studies", "Humans"])
    casos = _articulo("5", tipos_publicacion=["Observational Study"])
    assert cohorte.nivel_evidencia == "obs"
    assert casos.nivel_evidencia == "obs"


def test_diseno_transversal_o_editorial_no_suben_de_nivel():
    for kwargs in (
        {"mesh_descriptores": ["Cross-Sectional Studies"]},
        {"tipos_publicacion": ["Journal Article", "Editorial"]},
        {"tipos_publicacion": ["Case Reports"]},
    ):
        assert _articulo("6", **kwargs).nivel_evidencia == "otros"


def test_informe_ets_gana_sobre_el_eca_que_lo_sustenta():
    """Un ECA pragmático publicado como informe de agencia se reporta como ETS (nivel 1)."""
    art = _articulo(
        "7",
        tipos_publicacion=["Randomized Controlled Trial", "Health Technology Assessment"],
        titulo="Balloon angioplasty versus drug-coated balloon: an HTA report",
        revista_iso="Health Technol Assess",
        año=2025,
    )
    assert art.nivel_evidencia == "ets"
    assert art.nivel_orden == 1


def test_ets_por_descriptor_mesh_oficial():
    art = _articulo("8", mesh_descriptores=["Technology Assessment, Biomedical", "Humans"])
    assert art.nivel_evidencia == "ets"


def test_ets_por_frase_en_el_abstract():
    art = _articulo(
        "9",
        tipos_publicacion=["Journal Article"],
        abstract="This health technology assessment evaluated the cost-effectiveness of the intervention.",
    )
    assert art.nivel_evidencia == "ets"


def test_ets_por_revista_de_ets_con_evaluacion_economica():
    art = _articulo(
        "10",
        tipos_publicacion=["Journal Article"],
        titulo="Cost-utility of SGLT2 inhibitors in type 2 diabetes",
        revista_iso="Int J Technol Assess Health Care",
    )
    assert art.nivel_evidencia == "ets"


def test_un_eca_comun_no_se_confunde_con_ets_aunque_salga_en_revista_de_ets():
    """El solo hecho de publicarse en la revista NIHR no convierte un ECA en informe ETS."""
    art = _articulo(
        "11",
        tipos_publicacion=["Randomized Controlled Trial"],
        titulo="Plain balloon angioplasty versus drug-coated balloon angioplasty",
        revista_iso="Health Technol Assess",
    )
    assert art.nivel_evidencia == "rct"


# ------------------------------------------------------------------------- orden/cupos


def test_ordenar_por_calidad_respeta_la_jerarquia_y_luego_el_ano():
    articulos = [
        _articulo("a1", tipos_publicacion=["Observational Study"], año=2026),
        _articulo("a2", tipos_publicacion=["Randomized Controlled Trial"], año=2019),
        _articulo("a3", tipos_publicacion=["Meta-Analysis"], año=2021),
        _articulo("a4", tipos_publicacion=["Journal Article"], año=2026),
        _articulo("a5", tipos_publicacion=["Systematic Review"], año=2024),
    ]
    orden = evidence_service.ordenar_por_calidad(articulos)
    assert [a.pmid for a in orden] == ["a5", "a3", "a2", "a1", "a4"]


def test_resumen_por_nivel_incluye_todos_los_niveles():
    articulos = [_articulo("b1", tipos_publicacion=["Meta-Analysis"])]
    resumen = evidence_service.resumen_por_nivel(articulos)
    assert set(resumen) == set(evidence_service.ORDEN_NIVELES)
    assert resumen["rs_ma"] == 1
    assert resumen["ets"] == 0


def test_cotas_por_nivel_no_superan_el_maximo_y_dejan_hueco_por_nivel():
    for max_results in (4, 6, 10, 25):
        niveles = ["ets", "rs_ma", "rct", "obs"]
        cotas = evidence_service.cotas_por_nivel(max_results, niveles)
        assert set(cotas) == set(niveles)
        assert sum(cotas.values()) <= max_results
        assert all(v >= 1 for v in cotas.values())


def test_normalizar_niveles_ignora_codigos_inexistentes():
    assert evidence_service.normalizar_niveles(["rct", "astrologia"]) == ["rct"]
    assert evidence_service.normalizar_niveles(None) == ["ets", "rs_ma", "rct", "obs"]
    assert "otros" not in evidence_service.normalizar_niveles(["otros", "rct"])


# ---------------------------------------------------------------------------- queries


def test_clausulas_de_nivel_usan_solo_etiquetas_validadas():
    """
    Etiquetas confirmadas contra PubMed. Ojo: "Cohort Studies"[Publication Type] devuelve 0,
    los diseños observacionales se filtran como [MeSH Terms].
    """
    assert '"Cohort Studies"[MeSH Terms]' in evidence_service.CLAUSULAS_NIVEL["obs"]
    assert '"Case-Control Studies"[MeSH Terms]' in evidence_service.CLAUSULAS_NIVEL["obs"]
    assert '"Cohort Studies"[Publication Type]' not in evidence_service.CLAUSULAS_NIVEL["obs"]
    assert '"Meta-Analysis"[Publication Type]' in evidence_service.CLAUSULAS_NIVEL["rs_ma"]
    assert '"Randomized Controlled Trial"[Publication Type]' in evidence_service.CLAUSULAS_NIVEL["rct"]
    assert '"Technology Assessment, Biomedical"[MeSH Terms]' in evidence_service.CLAUSULAS_NIVEL["ets"]


def test_construir_query_nivel_parentiza_para_no_romper_la_precedencia():
    query = evidence_service.construir_query_nivel('(A[tiab]) AND (B[tiab])', "rs_ma")
    assert query.startswith("((A[tiab]) AND (B[tiab])) AND (")
    assert query.count("(") == query.count(")")
    # El OR del nivel va íntegro dentro de su propio paréntesis: si no, PubMed lo
    # expandiría a todo el índice y la búsqueda dejaría de ser PICO.
    separador = ") AND "
    # rindex: el primer ") AND " pertenece a la base PICO, el último introduce el nivel.
    clausula_nivel = query[query.rindex(separador) + len(separador):]
    assert clausula_nivel.startswith("(")
    assert clausula_nivel.endswith(")")
    assert clausula_nivel.count("(") == clausula_nivel.count(")")


def test_query_para_niveles_agrupa_varios_niveles():
    query = evidence_service.query_para_niveles("(A) AND (B)", ["rs_ma", "rct"])
    assert query.startswith("((A) AND (B)) AND (")
    assert '"Meta-Analysis"[Publication Type]' in query
    assert '"Randomized Controlled Trial"[Publication Type]' in query


# ------------------------------------------------------------------------ integración


@pytest.mark.asyncio
async def test_busqueda_por_niveles_real_devuelve_jerarquia_ordenada():
    """Búsqueda real: los niveles salen ordenados y con conteos coherentes."""
    from app.services import pubmed_service

    base = '("Diabetes Mellitus, Type 2"[MeSH Terms]) AND Empagliflozin[tiab]'
    niveles = ["ets", "rs_ma", "rct", "obs"]
    resultado = await pubmed_service.buscar_por_niveles(base, niveles, max_results=6)

    articulos = resultado["articulos"]
    assert len(articulos) > 0
    assert len(articulos) <= 6
    ordenes = [a.nivel_orden for a in articulos]
    assert ordenes == sorted(ordenes)
    assert resultado["total_base"] > 0
    assert set(resultado["totales_por_nivel"]) <= set(niveles)


def test_endpoint_pico_devuelve_niveles_y_vocabulario():
    """El endpoint expone el nivel de evidencia y los términos MeSH resueltos."""
    resp = client.post(
        "/api/v1/search/pico",
        json={
            "poblacion": "diabetes tipo 2",
            "intervencion": "metformina",
            "outcome": "mortalidad",
            "max_results": 4,
            "optimizar_con_ia": False,
            "usar_vocabulario_controlado": True,
            "priorizar_calidad": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["pregunta_clinica"].startswith("En diabetes tipo 2")
    assert data["terminos_clinicos"], "deben resolverse los términos PICO"
    resueltos = {t["entrada"]: t for t in data["terminos_clinicos"]}
    assert "diabetes tipo 2" in resueltos
    assert resueltos["diabetes tipo 2"]["descriptor"] == "Diabetes Mellitus, Type 2"
    assert resueltos["diabetes tipo 2"]["mesh_ui"] == "D003924"

    assert data["niveles_consultados"] == ["ets", "rs_ma", "rct", "obs"]
    assert set(data["distribucion_devueltos"]) == set(evidence_service.ORDEN_NIVELES)
    for art in data["articulos"]:
        assert art["nivel_evidencia"] in evidence_service.ORDEN_NIVELES
        assert art["nivel_etiqueta"]
        assert art["senal_nivel"]
