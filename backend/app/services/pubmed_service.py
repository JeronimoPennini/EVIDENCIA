"""
EvidencIA — Servicio PubMed
Consulta la API NCBI E-utilities para buscar y recuperar artículos científicos.
Documentación oficial: https://www.ncbi.nlm.nih.gov/books/NBK25497/
"""

import ssl
import httpx
import xml.etree.ElementTree as ET
from typing import Optional

# En Windows con Python 3.14, usar el trust store del sistema para verificar SSL
try:
    import truststore
    _SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:
    _SSL_CONTEXT = True  # comportamiento por defecto de httpx

from app.models.search import ArticleResult, Author, SearchResponse
from app.services import evidence_service
from app.config import get_settings

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _build_params(extra: dict) -> dict:
    """Agrega claves comunes a todos los requests NCBI."""
    settings = get_settings()
    params = {"retmode": "json", "tool": "EvidencIA", "email": settings.ncbi_email}
    # Solo enviar api_key si está configurada y no es un placeholder
    api_key = settings.ncbi_api_key.strip() if settings.ncbi_api_key else ""
    if api_key and not api_key.startswith("tu_clave"):
        params["api_key"] = api_key
    params.update(extra)
    return params


async def _esearch(
    client: httpx.AsyncClient,
    term: str,
    retmax: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[int, list[str]]:
    """Devuelve (total_de_articulos, pmids) para una query PubMed."""
    params = _build_params(
        {
            "db": "pubmed",
            "term": term,
            "retmax": retmax,
            "usehistory": "y",
        }
    )
    if date_from:
        params["mindate"] = date_from
    if date_to:
        params["maxdate"] = date_to

    resp = await client.get(f"{NCBI_BASE}/esearch.fcgi", params=params)
    resp.raise_for_status()
    result = resp.json().get("esearchresult", {})
    return int(result.get("count", 0)), list(result.get("idlist", []))


async def buscar_articulos(
    query: str,
    max_results: int = 10,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> SearchResponse:
    """
    Busca artículos en PubMed usando esearch + efetch.
    Retorna una SearchResponse con los artículos encontrados.
    """
    async with httpx.AsyncClient(timeout=30, verify=_SSL_CONTEXT) as client:
        # Paso 1: esearch — obtener lista de PMIDs
        total, pmids = await _esearch(client, query, max_results, date_from, date_to)

        if not pmids:
            return SearchResponse(query=query, total_encontrados=total, articulos=[])

        # Paso 2: efetch — recuperar detalles en XML
        articulos = await _fetch_articulos(client, pmids)

    return SearchResponse(query=query, total_encontrados=total, articulos=articulos)


async def buscar_por_niveles(
    query_base: str,
    niveles: list[str],
    max_results: int = 10,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[list[ArticleResult], dict[str, int], int]:
    """
    Busca nivel por nivel de la jerarquía (ETS → RS/MA → ECA → observacionales) y
    devuelve el conjunto priorizado, en lugar de dejar que el ranking por relevancia
    de PubMed sepulte los informes de alta calidad debajo de cientos de artículos menores.

    Retorna {"articulos", "totales_por_nivel", "total_base"}.
    """
    asignacion = evidence_service.cotas_por_nivel(max_results, niveles)
    totales: dict[str, int] = {}
    # (pmid, nivel_de_origen) en el orden de la jerarquía, sin repetidos
    seleccion: list[tuple[str, str]] = []
    vistos: set[str] = set()
    total_base = 0

    async with httpx.AsyncClient(timeout=45, verify=_SSL_CONTEXT) as client:
        # Total real de la pregunta PICO, para no informar como "total" el de un nivel
        try:
            total_base, _ = await _esearch(client, query_base, 0, date_from, date_to)
        except Exception:
            total_base = 0

        for nivel, cupo in asignacion.items():
            termino = evidence_service.construir_query_nivel(query_base, nivel)
            try:
                total, pmids = await _esearch(client, termino, cupo, date_from, date_to)
            except Exception:
                totales[nivel] = 0
                continue
            totales[nivel] = total
            for pmid in pmids:
                if pmid not in vistos:
                    vistos.add(pmid)
                    seleccion.append((pmid, nivel))

        # Los cupos se piden por nivel y los registros suelen solaparse entre niveles, así
        # que la suma suele quedar corta: se completa con la query combinada de la jerarquía.
        if len(seleccion) < max_results:
            combinada = evidence_service.query_para_niveles(query_base, niveles)
            try:
                _, pmids = await _esearch(client, combinada, max_results * 3, date_from, date_to)
            except Exception:
                pmids = []
            for pmid in pmids:
                if len(seleccion) >= max_results:
                    break
                if pmid not in vistos:
                    vistos.add(pmid)
                    seleccion.append((pmid, ""))

        if not seleccion:
            return {"articulos": [], "totales_por_nivel": totales, "total_base": total_base}

        # Un solo efetch para toda la selección priorizada
        articulos = await _fetch_articulos(client, [pmid for pmid, _ in seleccion])

    por_pmid = {a.pmid: a for a in articulos}
    resultados: list[ArticleResult] = []
    for pmid, nivel in seleccion:
        art = por_pmid.get(pmid)
        if art is not None:
            art.recuperado_por_nivel = nivel or art.nivel_evidencia
            resultados.append(art)

    return {
        "articulos": evidence_service.ordenar_por_calidad(resultados),
        "totales_por_nivel": totales,
        "total_base": total_base,
    }


async def _fetch_articulos(client: httpx.AsyncClient, pmids: list[str]) -> list[ArticleResult]:
    """Recupera detalles completos de una lista de PMIDs vía efetch."""
    fetch_params = _build_params(
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
        }
    )
    # Para efetch en XML necesitamos retmode=xml (sobreescribir json por defecto)
    fetch_params["retmode"] = "xml"

    fetch_resp = await client.get(f"{NCBI_BASE}/efetch.fcgi", params=fetch_params)
    fetch_resp.raise_for_status()

    return _parsear_xml(fetch_resp.text)


def _parsear_xml(xml_text: str) -> list[ArticleResult]:
    """Parsea el XML de PubMed y extrae campos relevantes de cada artículo."""
    articulos: list[ArticleResult] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return articulos

    for article in root.findall(".//PubmedArticle"):
        try:
            pmid = article.findtext(".//PMID") or ""
            titulo_el = article.find(".//ArticleTitle")
            titulo = "".join(titulo_el.itertext()).strip() if titulo_el is not None else "Sin título"

            # Abstract estructurado o simple
            abstract_parts: list[str] = []
            for ab_el in article.findall(".//AbstractText"):
                ab_text = "".join(ab_el.itertext()).strip()
                label = ab_el.get("Label")
                if label and ab_text:
                    abstract_parts.append(f"{label}: {ab_text}")
                elif ab_text:
                    abstract_parts.append(ab_text)
            abstract_text = "\n\n".join(abstract_parts)

            revista = article.findtext(".//Journal/Title") or ""
            revista_iso = article.findtext(".//Journal/ISOAbbreviation") or ""

            # Tipos de publicación y descriptores MeSH: materia prima del nivel de evidencia
            tipos_publicacion = [
                (pt.text or "").strip()
                for pt in article.findall(".//PublicationTypeList/PublicationType")
                if (pt.text or "").strip()
            ]
            mesh_descriptores = [
                (d.text or "").strip()
                for d in article.findall(".//MeshHeadingList/MeshHeading/DescriptorName")
                if (d.text or "").strip()
            ]

            # Año de publicación
            año_str = article.findtext(".//JournalIssue/PubDate/Year") or article.findtext(".//PubDate/Year") or ""
            if not año_str:
                medline_date = article.findtext(".//PubDate/MedlineDate") or ""
                # Extrae los primeros 4 dígitos si están presentes
                import re
                m = re.search(r"\b(19\d\d|20\d\d)\b", medline_date)
                if m:
                    año_str = m.group(1)
            año = int(año_str) if año_str.isdigit() else None

            # DOI
            doi = None
            for id_el in article.findall(".//ArticleId"):
                if id_el.get("IdType") == "doi":
                    doi = id_el.text

            # Autores
            autores: list[Author] = []
            afiliaciones: list[str] = []
            for author_el in article.findall(".//Author"):
                apellido = author_el.findtext("LastName") or ""
                nombre = author_el.findtext("ForeName") or ""
                afil = author_el.findtext(".//AffiliationInfo/Affiliation")
                if afil:
                    afiliaciones.append(afil)
                nombre_completo = f"{apellido}, {nombre}".strip(", ")
                if nombre_completo:
                    autores.append(Author(nombre=nombre_completo, afiliacion=afil))

            # Colaboraciones corporativas (también delatan agencias de ETS)
            for collectivo in article.findall(".//Author/CollectiveName"):
                if (collectivo.text or "").strip():
                    afiliaciones.append(collectivo.text.strip())

            articulo = ArticleResult(
                pmid=pmid,
                titulo=titulo,
                autores=autores,
                revista=revista,
                año=año,
                abstract=abstract_text,
                doi=doi,
                url_pubmed=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                revista_iso=revista_iso,
                tipos_publicacion=tipos_publicacion,
                mesh_descriptores=mesh_descriptores,
                afiliaciones=" | ".join(afiliaciones),
            )
            articulos.append(evidence_service.aplicar_clasificacion(articulo))
        except Exception:
            # Si un artículo falla, continuamos con el resto
            continue

    return articulos


async def fetch_por_pmids(pmids: list[str]) -> list[ArticleResult]:
    """Recupera artículos dado una lista de PMIDs (usado por el motor de síntesis)."""
    async with httpx.AsyncClient(timeout=30, verify=_SSL_CONTEXT) as client:
        return await _fetch_articulos(client, pmids)
