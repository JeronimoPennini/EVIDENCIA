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
        search_params = _build_params(
            {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "usehistory": "y",
            }
        )
        if date_from:
            search_params["mindate"] = date_from
        if date_to:
            search_params["maxdate"] = date_to

        search_resp = await client.get(f"{NCBI_BASE}/esearch.fcgi", params=search_params)
        search_resp.raise_for_status()
        search_data = search_resp.json()

        esearch = search_data.get("esearchresult", {})
        pmids: list[str] = esearch.get("idlist", [])
        total = int(esearch.get("count", 0))

        if not pmids:
            return SearchResponse(query=query, total_encontrados=total, articulos=[])

        # Paso 2: efetch — recuperar detalles en XML
        articulos = await _fetch_articulos(client, pmids)

    return SearchResponse(query=query, total_encontrados=total, articulos=articulos)


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
            for author_el in article.findall(".//Author"):
                apellido = author_el.findtext("LastName") or ""
                nombre = author_el.findtext("ForeName") or ""
                afil = author_el.findtext(".//AffiliationInfo/Affiliation")
                nombre_completo = f"{apellido}, {nombre}".strip(", ")
                if nombre_completo:
                    autores.append(Author(nombre=nombre_completo, afiliacion=afil))

            articulos.append(
                ArticleResult(
                    pmid=pmid,
                    titulo=titulo,
                    autores=autores,
                    revista=revista,
                    año=año,
                    abstract=abstract_text,
                    doi=doi,
                    url_pubmed=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )
        except Exception:
            # Si un artículo falla, continuamos con el resto
            continue

    return articulos


async def fetch_por_pmids(pmids: list[str]) -> list[ArticleResult]:
    """Recupera artículos dado una lista de PMIDs (usado por el motor de síntesis)."""
    async with httpx.AsyncClient(timeout=30, verify=_SSL_CONTEXT) as client:
        return await _fetch_articulos(client, pmids)
