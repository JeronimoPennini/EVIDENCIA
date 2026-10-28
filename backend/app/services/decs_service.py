"""
EvidencIA — Vocabulario controlado DeCS / MeSH

Resuelve términos clínicos en español contra descriptores MeSH canónicos para que las
queries PubMed usen `[MeSH Terms]` válidos en lugar de texto libre mal traducido.

Fuentes usadas (verificadas manualmente el 2026-10-28):

1. **DeCS API oficial (BIREME/OPS)** — `https://api.bvsalud.org/decs/v2/`
   Endpoints `GET /search-by-words`, `GET /search-boolean`, `GET /get-tree`, con `lang=es`.
   Requiere la apikey de BIREME en la cabecera `apikey` (licencia gratuita, formulario en
   https://decs.bvsalud.org/es/condiciones-para-descargar-los-datos-de-decs-mesh/).
   Sin clave responde 401, por eso se omite automáticamente.
   Espec: https://docs.api.bvsalud.org/apis/decs-es.yaml

2. **NCBI MeSH (E-utilities `db=mesh`)** — sin clave. El `translationset` de `esearch`
   devuelve el descriptor canónico: p.ej. `type 2 diabetes` →
   `"diabetes mellitus, type 2"[MeSH Terms]`.

3. **NLM MeSH Lookup API** — sin clave.
   `https://id.nlm.nih.gov/mesh/lookup/descriptor?label=...&match=exact|startswith|contains`
   Confirma el descriptor y su número de registro (D003924).

Los resultados se cachean en `backend/data/vocab_cache.json` (TTL 30 días) para no repetir
llamadas y respetar el rate limit de NCBI (3 req/s sin apikey).
"""

import asyncio
import json
import re
import ssl
import time
from pathlib import Path
from typing import Any, Optional

import httpx

try:
    import truststore
    _SSL_CONTEXT: Any = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:  # pragma: no cover - depende del entorno
    _SSL_CONTEXT = True

from app.config import get_settings
from app.models.search import TerminoClinico
from app.services.diccionario_es_en import traducir_termino

NLM_LOOKUP_URL = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "vocab_cache.json"
CACHE_TTL_SEGUNDOS = 30 * 24 * 3600

# NCBI sin api_key admite ~3 solicitudes por segundo: se limita a 2 con este semáforo.
_SEMAFORO = asyncio.Semaphore(2)
_CACHE: Optional[dict[str, dict[str, Any]]] = None
_BLOQUEO_CACHE = asyncio.Lock()


# --------------------------------------------------------------------------- cache


def _cargar_cache() -> dict[str, dict[str, Any]]:
    """Lee la caché persistida en disco; si no existe o está corrupta, devuelve vacía."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    datos: dict[str, dict[str, Any]] = {}
    if CACHE_PATH.exists():
        try:
            crudo = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            ahora = time.time()
            datos = {
                k: v
                for k, v in crudo.items()
                if isinstance(v, dict) and ahora - float(v.get("ts", 0)) < CACHE_TTL_SEGUNDOS
            }
        except Exception:
            datos = {}
    _CACHE = datos
    return _CACHE


def _guardar_cache() -> None:
    """Escribe la caché en disco de forma atómica (mejor esfuerzo, nunca interrumpe la búsqueda)."""
    assert _CACHE is not None
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(_CACHE, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(CACHE_PATH)
    except Exception:
        pass


async def _cache_get(clave: str) -> Optional[dict[str, Any]]:
    async with _BLOQUEO_CACHE:
        entrada = _cargar_cache().get(clave)
    if not entrada:
        return None
    if time.time() - float(entrada.get("ts", 0)) > CACHE_TTL_SEGUNDOS:
        return None
    return entrada.get("valor")


async def _cache_set(clave: str, valor: dict[str, Any]) -> None:
    async with _BLOQUEO_CACHE:
        _cargar_cache()[clave] = {"ts": time.time(), "valor": valor}
        _guardar_cache()


# ---------------------------------------------------------------------- http común


async def _get_json(url: str, params: dict[str, str], headers: Optional[dict[str, str]] = None) -> Any:
    """GET con límites de concurrencia, separación entre llamadas y un rebote final."""
    ultimo_error: Optional[Exception] = None
    async with _SEMAFORO:
        for intento in range(2):
            try:
                async with httpx.AsyncClient(timeout=25, verify=_SSL_CONTEXT) as client:
                    resp = await client.get(url, params=params, headers=headers or {})
                    resp.raise_for_status()
                    return resp.json()
            except Exception as error:  # NCBI/NLM devuelven 5xx o cortan la conexión a veces
                ultimo_error = error
                await asyncio.sleep(1.2 * (intento + 1))
            finally:
                await asyncio.sleep(0.35)
    assert ultimo_error is not None
    raise ultimo_error


# --------------------------------------------------------------- 3) NLM MeSH lookup


async def buscar_descriptor_nlm(frase: str, match: str = "exact") -> Optional[dict[str, str]]:
    """
    Busca un descriptor MeSH por etiqueta. Retorna {'label', 'ui'} o None.
    `match` admite exact | startswith | contains.
    """
    if not frase or len(frase.strip()) < 3:
        return None
    clave = f"nlm:{match}:{frase.strip().lower()}"
    en_cache = await _cache_get(clave)
    if en_cache is not None:
        return en_cache or None

    try:
        datos = await _get_json(
            NLM_LOOKUP_URL, {"label": frase.strip(), "match": match, "limit": "1"}
        )
    except Exception:
        return None

    encontrado = None
    if isinstance(datos, list) and datos:
        recurso = str(datos[0].get("resource", ""))
        encontrado = {
            "label": datos[0].get("label", frase),
            "ui": recurso.rsplit("/", 1)[-1] if recurso else "",
        }
    await _cache_set(clave, encontrado or {})
    return encontrado


# ---------------------------------------------------------- 2) NCBI MeSH (db=mesh)


_RE_MESH_TRADUCIDO = re.compile(r'"([^"]+)"\[MeSH Terms\]', re.IGNORECASE)


async def traducir_a_descriptor_ncbi(frase_ingles: str) -> Optional[str]:
    """
    Pregunta al índice MeSH de NCBI por una frase en inglés y devuelve la etiqueta
    del descriptor canónico al que PubMed la traduce (o None si no tiene descriptor).
    """
    frase = frase_ingles.strip()
    if not frase:
        return None
    clave = f"ncbi_mesh:{frase.lower()}"
    en_cache = await _cache_get(clave)
    if en_cache is not None:
        return en_cache.get("descriptor") or None

    params = {
        "db": "mesh",
        # Se consulta la frase SIN comillas: citada, PubMed deja de traducirla al descriptor.
        "term": frase,
        "retmode": "json",
        "retmax": "1",
    }
    settings = get_settings()
    if settings.ncbi_api_key and not settings.ncbi_api_key.startswith("tu_clave"):
        params["api_key"] = settings.ncbi_api_key.strip()

    descriptor = None
    try:
        datos = await _get_json(f"{EUTILS_BASE}/esearch.fcgi", params)
        result = datos.get("esearchresult", {}) if isinstance(datos, dict) else {}
        for traduccion in result.get("translationset", []) or []:
            coincidencia = _RE_MESH_TRADUCIDO.search(str(traduccion.get("to", "")))
            if coincidencia:
                descriptor = coincidencia.group(1)
                break
    except Exception:
        descriptor = None

    await _cache_set(clave, {"descriptor": descriptor or ""})
    return descriptor


# ---------------------------------------------------------------- 1) DeCS oficial


async def resolver_por_decs(texto: str) -> Optional[dict[str, str]]:
    """
    Consulta la API DeCS de BIREME en español y devuelve {'decs', 'mesh', 'ui'} o None.
    Se omite si no hay DECS_API_KEY configurada. El análisis del payload es tolerante
    porque el cuerpo de la respuesta sólo puede validarse con una apikey vigente.
    """
    settings = get_settings()
    apikey = (settings.decs_api_key or "").strip()
    if not apikey or apikey.startswith("tu_clave"):
        return None

    clave = f"decs:{texto.strip().lower()}"
    en_cache = await _cache_get(clave)
    if en_cache is not None:
        return en_cache or None

    try:
        datos = await _get_json(
            f"{settings.decs_api_base.rstrip('/')}/search-by-words",
            {"words": texto.strip(), "lang": "es", "format": "json"},
            headers={"apikey": apikey},
        )
    except Exception:
        await _cache_set(clave, {})
        return None

    resuelto = _extraer_decs(datos)
    await _cache_set(clave, resuelto or {})
    return resuelto


def _extraer_decs(payload: Any) -> Optional[dict[str, str]]:
    """
    Extrae el primer descriptor DeCS de la respuesta de la API.
    Busca recursivamente un nodo con nombre en español y su equivalente MeSH/UI.
    """
    candidatos: list[dict[str, Any]] = []

    def recorrer(nodo: Any) -> None:
        if isinstance(nodo, dict):
            keys = {k.lower(): v for k, v in nodo.items()}
            nombre_es = (
                keys.get("descriptor")
                or keys.get("decs")
                or keys.get("tituloes")
                or keys.get("title_es")
                or keys.get("nombre")
                or keys.get("name")
                or keys.get("label")
            )
            mesh_en = (
                keys.get("mesh")
                or keys.get("descriptormesh")
                or keys.get("titleen")
                or keys.get("title_en")
                or keys.get("descriptorname")
                or keys.get("meshname")
                or keys.get("mesh_label")
            )
            ui = keys.get("meshnumber") or keys.get("mesh_number") or keys.get("ui") or keys.get("descriptorui")
            if nombre_es or mesh_en:
                candidatos.append(
                    {
                        "decs": str(nombre_es or mesh_en or ""),
                        "mesh": str(mesh_en or nombre_es or ""),
                        "ui": str(ui or ""),
                    }
                )
            for valor in nodo.values():
                recorrer(valor)
        elif isinstance(nodo, list):
            for item in nodo:
                recorrer(item)

    recorrer(payload)
    return candidatos[0] if candidatos else None


# ------------------------------------------------------------------ resolución


_RE_MESH_TERMS = re.compile(r'"([^"]+)"\s*\[\s*MeSH\s+Terms?\s*\]', re.IGNORECASE)


def _normalizar_etiqueta(label: str) -> str:
    """Pone el descriptor en notación de título tal como lo publica MeSH."""
    return " ".join(label.strip().split())


_PALABRAS_VACIAS_EN = {
    "of", "the", "a", "an", "and", "or", "in", "on", "with", "for", "as", "to",
}


def _palabras(texto: str) -> set[str]:
    return {
        w for w in re.sub(r"[^\w\s\-]", " ", (texto or "").lower()).split()
        if w and w not in _PALABRAS_VACIAS_EN and len(w) > 1
    }


def _coherente(label: str, consulta: str) -> bool:
    """
    Control de sensibilidad para coincidencias parciales (startswith/contains).

    Un descriptor hallado de forma parcial sólo se acepta si todas sus palabras aparecen
    en la consulta original. Evita que `placebo` cierre contra "Placebo Effect" o que una
    población genérica se indexe contra un descriptor más amplio y poco específico.
    Las coincidencias exactas no pasan por este filtro.
    """
    palabras_label = _palabras(label)
    palabras_consulta = _palabras(consulta)
    if not palabras_label or not palabras_consulta:
        return False
    return palabras_label <= palabras_consulta


def construir_clausura(frase_original: str, descriptor: Optional[str], texto_en: str) -> str:
    """
    Construye la cláusura PubMed: búsqueda por descriptor MeSH + texto libre en inglés
    como respaldo (auto-translation de PubMed ya expande sinónimos, pero la cláusula
    explícita mejora el recall cuando el descriptor no cubre el término).

    Con frases largas la cita textual entre comillas casi nunca casa literalmente, así
    que se reemplaza por la conjunción de sus palabras en [tiab].
    """
    partes: list[str] = []
    if descriptor:
        partes.append(f'"{_normalizar_etiqueta(descriptor)}"[MeSH Terms]')
    if texto_en:
        palabras = [w for w in re.sub(r"[^\w\- ]", " ", texto_en).split() if w]
        if len(palabras) == 1:
            partes.append(f"{palabras[0]}[tiab]")
        elif len(palabras) >= 3:
            # La frase textual casi nunca aparece literalmente en los abstracts: se suma
            # la conjunción de sus palabras para no perder recall.
            unidas = " AND ".join(f"{w}[tiab]" for w in palabras)
            partes.append(f'("{" ".join(palabras)}"[tiab] OR ({unidas}))')
        elif palabras:
            partes.append(f'"{ " ".join(palabras) }"[tiab]')
    if not partes:
        limpio = re.sub(r"[^\w\- ]", " ", frase_original).strip()
        partes.append(f'"{limpio}"[tiab]' if limpio else '""[tiab]')
    return "(" + " OR ".join(partes) + ")"


async def resolver_termino(texto: str) -> TerminoClinico:
    """
    Resuelve un término clínico (español o inglés) contra el vocabulario controlado.

    Prioridad: DeCS oficial (si hay apikey) → traducción ES→EN del diccionario local →
    validación contra NLM MeSH → traducción MeSH de NCBI → sin resolver (texto libre).
    """
    texto_limpio = (texto or "").strip()
    if not texto_limpio:
        return TerminoClinico(entrada="", fuente="vacio")

    # 1) DeCS oficial: es la única fuente con equivalencia español -> MeSH verificada.
    decs = await resolver_por_decs(texto_limpio)
    if decs and decs.get("mesh"):
        mesh = _normalizar_etiqueta(decs["mesh"])
        ui = decs.get("ui") or ""
        if not ui:
            verificado = await buscar_descriptor_nlm(mesh)
            ui = verificado["ui"] if verificado else ""
        return TerminoClinico(
            entrada=texto_limpio,
            descriptor=mesh,
            mesh_ui=ui,
            decs_nombre=decs.get("decs") or "",
            fuente="decs",
            clausura=construir_clausura(texto_limpio, mesh, mesh),
        )

    # 2) Traducir con el diccionario local (o venir ya en inglés).
    texto_en = traducir_termino(texto_limpio) or texto_limpio

    # 3) Validar contra NLM MeSH (etiqueta exacta, luego coincidencias parciales filtradas).
    descriptor: Optional[str] = None
    ui = ""
    for match in ("exact", "startswith", "contains"):
        hallado = await buscar_descriptor_nlm(texto_en, match=match)
        if not hallado:
            continue
        if match != "exact" and not _coherente(hallado["label"], texto_en):
            continue
        descriptor = hallado["label"]
        ui = hallado["ui"]
        break

    # 4) Si no cerró, pedir a NCBI el descriptor al que PubMed traduce la frase.
    if not descriptor:
        canonico = await traducir_a_descriptor_ncbi(texto_en)
        if canonico:
            verificado = await buscar_descriptor_nlm(canonico)
            descriptor = verificado["label"] if verificado else canonico
            ui = verificado["ui"] if verificado else ""

    fuente = "mesh" if descriptor else "diccionario"
    return TerminoClinico(
        entrada=texto_limpio,
        descriptor=descriptor or "",
        mesh_ui=ui,
        decs_nombre="",
        fuente=fuente,
        clausura=construir_clausura(texto_limpio, descriptor, texto_en),
    )


async def resolver_terminos(textos: list[str]) -> list[TerminoClinico]:
    """Resuelve varios términos en paralelo, preservando el orden de entrada."""
    return list(await asyncio.gather(*(resolver_termino(t) for t in textos)))


async def _corregir_descriptor(frase: str) -> str:
    """Devuelve la cláusula correcta para una frase citada como [MeSH Terms]."""
    exacto = await buscar_descriptor_nlm(frase)
    if exacto:
        return f'"{_normalizar_etiqueta(exacto["label"])}"[MeSH Terms]'
    canonico = await traducir_a_descriptor_ncbi(frase)
    if canonico:
        verificada = await buscar_descriptor_nlm(canonico)
        etiqueta = _normalizar_etiqueta(verificada["label"] if verificada else canonico)
        return f'"{etiqueta}"[MeSH Terms]'
    return f'"{frase}"[tiab]'


async def reparar_query(query: str) -> tuple[str, list[str]]:
    """
    Corrige descriptores MeSH inválidos dentro de una query ya construida.

    `"type 2 diabetes"[MeSH Terms]` devuelve 0 resultados en PubMed porque el descriptor
    real es `"Diabetes Mellitus, Type 2"`. Esta función reemplaza cada frase citada con
    `[MeSH Terms]` por el descriptor canónico; si no existe descriptor, degrada la cláusula
    a texto libre `[tiab]` para que la búsqueda no quede vacía.

    Retorna (query_corregida, lista_de_cambios_legibles).
    """
    cambios: list[str] = []
    if not query or "[mesh" not in query.lower():
        return query, cambios

    coincidencias = list(_RE_MESH_TERMS.finditer(query))
    if not coincidencias:
        return query, cambios

    corregidas = await asyncio.gather(*[_corregir_descriptor(c.group(1)) for c in coincidencias])

    nueva_query = query
    for coincidencia, reemplazo in zip(coincidencias, corregidas):
        if reemplazo != coincidencia.group(0):
            cambios.append(f"{coincidencia.group(0)} -> {reemplazo}")
            nueva_query = nueva_query.replace(coincidencia.group(0), reemplazo, 1)

    return nueva_query, cambios


async def estado_vocabulario() -> dict[str, Any]:
    """Diagnóstico de las fuentes de vocabulario, usado por /health."""
    settings = get_settings()
    hay_decs = bool((settings.decs_api_key or "").strip()) and not settings.decs_api_key.startswith("tu_clave")
    return {
        "decs_api_key_configurada": hay_decs,
        "decs_api_base": settings.decs_api_base,
        "mesh_api": NLM_LOOKUP_URL,
        "cache_terminos": len(_cargar_cache()),
    }
