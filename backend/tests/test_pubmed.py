"""
EvidencIA — Tests del servicio PubMed
Verifica búsqueda real contra NCBI E-utilities (sin clave API necesaria).
"""

import pytest
import pytest_asyncio
from app.services.pubmed_service import buscar_articulos, fetch_por_pmids


@pytest.mark.asyncio
async def test_busqueda_basica():
    """Busca artículos reales en PubMed y verifica la estructura de la respuesta."""
    resultado = await buscar_articulos(query="metformin diabetes", max_results=3)

    assert resultado.total_encontrados > 0
    assert len(resultado.articulos) <= 3
    assert resultado.query == "metformin diabetes"


@pytest.mark.asyncio
async def test_articulo_tiene_campos():
    """Verifica que los artículos devueltos tienen los campos esenciales."""
    resultado = await buscar_articulos(query="aspirin cardiovascular", max_results=2)

    assert len(resultado.articulos) >= 1
    art = resultado.articulos[0]

    assert art.pmid != ""
    assert art.titulo != ""
    assert art.url_pubmed.startswith("https://pubmed.ncbi.nlm.nih.gov/")


@pytest.mark.asyncio
async def test_busqueda_sin_resultados():
    """Una búsqueda con términos sin sentido debe retornar lista vacía sin errores."""
    resultado = await buscar_articulos(
        query="xyzxyzxyz_termino_inexistente_12345", max_results=5
    )
    assert resultado.total_encontrados == 0
    assert resultado.articulos == []


@pytest.mark.asyncio
async def test_fetch_por_pmid_conocido():
    """Recupera un artículo por PMID conocido (artículo clásico de PubMed)."""
    # PMID 11207864: articulo clásico de acceso público
    articulos = await fetch_por_pmids(["11207864"])

    assert len(articulos) == 1
    assert articulos[0].pmid == "11207864"
    assert articulos[0].titulo != ""
