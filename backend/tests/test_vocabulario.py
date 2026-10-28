"""
EvidencIA — Tests del vocabulario controlado DeCS/MeSH

Las unidades se prueban sin red (se sustituyen las llamadas HTTP). Se incluye además
un test de integración contra la API abierta de MeSH, que no requiere ninguna clave.
"""

import pytest

from app.services import decs_service


@pytest.fixture(autouse=True)
def _cache_en_memoria(tmp_path, monkeypatch):
    """Evita escribir la caché real del proyecto durante los tests."""
    monkeypatch.setattr(decs_service, "CACHE_PATH", tmp_path / "vocab_cache.json")
    monkeypatch.setattr(decs_service, "_CACHE", None)


# ------------------------------------------------------------------ clausuras PubMed


def test_clausura_usa_descriptor_y_texto_libre():
    clausura = decs_service.construir_clausura(
        "diabetes tipo 2", "Diabetes Mellitus, Type 2", "Diabetes Mellitus Type 2"
    )
    assert '"Diabetes Mellitus, Type 2"[MeSH Terms]' in clausura
    assert '[tiab]' in clausura
    assert clausura.startswith("(") and clausura.endswith(")")


def test_clausura_sin_descriptor_usa_solo_texto_libre():
    clausura = decs_service.construir_clausura("empagliflozina", None, "empagliflozin")
    assert clausura == "(empagliflozin[tiab])"
    assert "MeSH" not in clausura


def test_clausura_de_frase_larga_combina_frase_y_palabras():
    """Una frase de 3+ palabras citada literalmente casi nunca casa: se complementa con AND."""
    clausura = decs_service.construir_clausura(
        "hospitalización por insuficiencia cardíaca", "Heart Failure",
        "hospitalization heart failure",
    )
    assert '"Heart Failure"[MeSH Terms]' in clausura
    assert '"hospitalization heart failure"[tiab]' in clausura
    assert "(hospitalization[tiab] AND heart[tiab] AND failure[tiab])" in clausura


def test_clausura_de_dos_palabras_va_como_frase():
    clausura = decs_service.construir_clausura("asma", None, "severe asthma")
    assert clausura == '("severe asthma"[tiab])'


def test_coherencia_rechaza_descriptores_demasiado_amplios():
    assert decs_service._coherente("Heart Failure", "heart failure with preserved ejection fraction")
    assert not decs_service._coherente("Placebo Effect", "placebo")
    assert not decs_service._coherente("Diabetes Mellitus, Type 1", "diabetes")


# ------------------------------------------------------------------------ reparación


@pytest.mark.asyncio
async def test_reparar_query_sustituye_descriptor_inventado(monkeypatch):
    async def falso_lookup(frase, match="exact"):
        if match == "exact" and frase.lower() == "diabetes mellitus, type 2":
            return {"label": "Diabetes Mellitus, Type 2", "ui": "D003924"}
        return None

    async def falso_traductor(frase):
        return "Diabetes Mellitus, Type 2" if frase.lower() == "type 2 diabetes" else None

    monkeypatch.setattr(decs_service, "buscar_descriptor_nlm", falso_lookup)
    monkeypatch.setattr(decs_service, "traducir_a_descriptor_ncbi", falso_traductor)

    original = '("type 2 diabetes"[MeSH Terms] AND "empagliflozin"[tiab])'
    corregida, cambios = await decs_service.reparar_query(original)

    assert '"Diabetes Mellitus, Type 2"[MeSH Terms]' in corregida
    assert '"type 2 diabetes"[MeSH Terms]' not in corregida
    assert "[tiab]" in corregida  # el resto de la query no se toca
    assert any("type 2 diabetes" in c for c in cambios)


@pytest.mark.asyncio
async def test_reparar_query_degrada_a_texto_libre_sin_descriptor(monkeypatch):
    async def sin_nada(frase, match="exact"):
        return None

    async def sin_traduccion(frase):
        return None

    monkeypatch.setattr(decs_service, "buscar_descriptor_nlm", sin_nada)
    monkeypatch.setattr(decs_service, "traducir_a_descriptor_ncbi", sin_traduccion)

    corregida, cambios = await decs_service.reparar_query('("HFpEF"[MeSH Terms])')
    assert corregida == '("HFpEF"[tiab])'
    assert cambios and "MeSH Terms" in cambios[0]


@pytest.mark.asyncio
async def test_reparar_query_no_toca_queries_sin_mesh(monkeypatch):
    called = False

    async def no_deberia_llamar(frase, match="exact"):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(decs_service, "buscar_descriptor_nlm", no_deberia_llamar)
    corregida, cambios = await decs_service.reparar_query("(diabetes) AND (metformin)")
    assert corregida == "(diabetes) AND (metformin)"
    assert cambios == []
    assert not called


# ------------------------------------------------------------------- resolución (mock)


@pytest.mark.asyncio
async def test_resolver_termino_prefiere_decs_cuando_hay_clave(monkeypatch):
    settings = decs_service.get_settings()
    monkeypatch.setattr(settings, "decs_api_key", "clave_de_prueba", raising=False)

    async def falso_decs(texto):
        return {"decs": "Diabetes Mellitus Tipo 2", "mesh": "Diabetes Mellitus, Type 2", "ui": "D003924"}

    llamado = {"nlm": False}

    async def falso_lookup(frase, match="exact"):
        llamado["nlm"] = True
        return None

    monkeypatch.setattr(decs_service, "resolver_por_decs", falso_decs)
    monkeypatch.setattr(decs_service, "buscar_descriptor_nlm", falso_lookup)

    term = await decs_service.resolver_termino("diabetes tipo 2")
    assert term.fuente == "decs"
    assert term.descriptor == "Diabetes Mellitus, Type 2"
    assert term.mesh_ui == "D003924"
    assert term.decs_nombre == "Diabetes Mellitus Tipo 2"
    assert '"Diabetes Mellitus, Type 2"[MeSH Terms]' in term.clausura
    # Con DeCS confirmado no hace falta validar contra NLM
    assert llamado["nlm"] is False


def _palabras(texto: str) -> set[str]:
    return set(texto.lower().replace(",", " ").split())


_DIABETES = {"diabetes", "mellitus", "type", "2"}


@pytest.mark.asyncio
async def test_resolver_termino_sin_decs_usa_diccionario_y_mesh(monkeypatch):
    async def sin_decs(texto):
        return None

    vistos: list[tuple[str, str]] = []

    async def falso_lookup(frase, match="exact"):
        vistos.append((frase, match))
        # NLM responde sin importar mayúsculas ni la coma del rótulo MeSH
        if _palabras(frase) == _DIABETES:
            return {"label": "Diabetes Mellitus, Type 2", "ui": "D003924"}
        return None

    async def sin_traduccion_ncbi(frase):
        return None

    monkeypatch.setattr(decs_service, "resolver_por_decs", sin_decs)
    monkeypatch.setattr(decs_service, "buscar_descriptor_nlm", falso_lookup)
    monkeypatch.setattr(decs_service, "traducir_a_descriptor_ncbi", sin_traduccion_ncbi)

    term = await decs_service.resolver_termino("diabetes tipo 2")
    assert term.fuente == "mesh"
    assert term.descriptor == "Diabetes Mellitus, Type 2"
    assert term.mesh_ui == "D003924"
    assert term.entrada == "diabetes tipo 2"
    # El diccionario local tradujo al inglés antes de consultar MeSH
    assert vistos and _palabras(vistos[0][0]) == _DIABETES


@pytest.mark.asyncio
async def test_resolver_termino_cierra_con_traduccion_ncbi(monkeypatch):
    """Cuando NLM no conoce la frase, se usa el descriptor canónico de NCBI db=mesh."""
    async def sin_decs(texto):
        return None

    async def lookup_solo_si_es_canonica(frase, match="exact"):
        if _palabras(frase) == _DIABETES:
            return {"label": "Diabetes Mellitus, Type 2", "ui": "D003924"}
        return None

    async def traductor_ncbi(frase):
        return "diabetes mellitus, type 2"  # PubMed devuelve el descriptor en minúsculas

    consultado: list[str] = []

    async def registrar_y_traducir(frase):
        consultado.append(frase)
        return await traductor_ncbi(frase)

    monkeypatch.setattr(decs_service, "resolver_por_decs", sin_decs)
    monkeypatch.setattr(decs_service, "buscar_descriptor_nlm", lookup_solo_si_es_canonica)
    monkeypatch.setattr(decs_service, "traducir_a_descriptor_ncbi", registrar_y_traducir)

    term = await decs_service.resolver_termino("diabetes tipo 2 no conocida")
    assert term.fuente == "mesh"
    assert term.descriptor == "Diabetes Mellitus, Type 2"
    # Se cayó al traductor de NCBI porque la frase larga no es un rótulo MeSH
    assert consultado


def test_extraer_decs_tolerante_a_formas_de_respuesta():
    """El parser de DeCS acepta las variantes de campo documentadas en el OpenAPI."""
    payloads = [
        [{"descriptor": "Diabetes Mellitus Tipo 2", "mesh": "Diabetes Mellitus, Type 2", "meshNumber": "D003924"}],
        {"descriptores": [{"tituloES": "Dolor", "titleEN": "Pain", "ui": "D012345"}]},
        {"data": {"list": [{"name": "Cefalgia", "meshName": "Headache", "descriptorUI": "D006260"}]}},
    ]
    esperados = [
        ("Diabetes Mellitus Tipo 2", "Diabetes Mellitus, Type 2", "D003924"),
        ("Dolor", "Pain", "D012345"),
        ("Cefalgia", "Headache", "D006260"),
    ]
    for payload, (decs, mesh, ui) in zip(payloads, esperados):
        resultado = decs_service._extraer_decs(payload)
        assert resultado == {"decs": decs, "mesh": mesh, "ui": ui}


def test_extraer_decs_con_respuesta_inesperada():
    assert decs_service._extraer_decs({"error": "invalid apikey"}) is None
    assert decs_service._extraer_decs([]) is None


def test_diccionario_local_ignora_tildes_y_mayusculas():
    from app.services.diccionario_es_en import traducir_termino

    assert traducir_termino("Hipertensión Arterial") == "hypertension"
    assert traducir_termino("hipertension arterial") == "hypertension"
    assert "empagliflozin" in traducir_termino("Empagliflozina")


# ------------------------------------------------------------------------ integración


@pytest.mark.asyncio
async def test_integracion_malla_real_type_2_diabetes():
    """
    `"type 2 diabetes"[MeSH Terms]` devuelve 0 en PubMed; el resolver debe cerrar contra
    el descriptor real "Diabetes Mellitus, Type 2" (D003924). Sin clave API de por medio.
    """
    descriptor = await decs_service.traducir_a_descriptor_ncbi("type 2 diabetes")
    assert descriptor is not None
    assert descriptor.lower() == "diabetes mellitus, type 2"

    verificado = await decs_service.buscar_descriptor_nlm("Diabetes Mellitus, Type 2")
    assert verificado == {"label": "Diabetes Mellitus, Type 2", "ui": "D003924"}


@pytest.mark.asyncio
async def test_integracion_terminos_resueltos_en_cadena():
    term = await decs_service.resolver_termino("hipertensión arterial")
    assert term.descriptor.lower() == "hypertension"
    assert '"Hypertension"[MeSH Terms]' in term.clausura
