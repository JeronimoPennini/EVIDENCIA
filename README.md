# EvidencIA

> Aplicación de síntesis de evidencia científica en salud asistida por IA.
> Stack: **Flutter (web)** + **Python 3.14 / FastAPI** · Herramientas gratuitas.

---

## Estructura del proyecto

```
EVIDENCIA/
├── .github/workflows/web.yml   # CI: build Flutter web → GitHub Pages
├── render.yaml       # Blueprint de Render (está en la raíz del repo a propósito)
├── build_web.bat     # flutter build web --dart-define=API_BASE_URL=...
├── iniciar_proyecto.bat / iniciar_backend.bat / iniciar_frontend.bat
├── Dockerfile        # Imagen del backend (contexto = raíz del repo; lo usa Render)
├── .dockerignore
├── backend/          # API Python + FastAPI
│   ├── main.py
│   ├── server_start.py   # arranque para hosting (respeta PORT)
│   ├── requirements.txt
│   ├── .env.example  # Plantilla de claves (nunca versionar .env)
│   ├── data/         # Caché de vocabulario DeCS/MeSH (generada, no versionada)
│   └── app/
│       ├── config.py     # settings: claves, PORT, CORS
│       ├── models/   # search.py (incluye TerminoClinico y niveles), synthesis.py
│       ├── routers/
│       └── services/
│           ├── decs_service.py        # DeCS + NLM MeSH Lookup + db=mesh
│           ├── diccionario_es_en.py   # diccionario local de respaldo
│           ├── evidence_service.py    # jerarquía ETS > RS/MA > ECA > observacional
│           ├── pubmed_service.py      # esearch por nivel + efetch + clasificación
│           ├── pico_service.py        # orquesta IA + vocabulario + búsqueda
│           ├── gemini_service.py      # cliente Gemini
│           └── synthesis_service.py   # prompt de síntesis jerarquizada
└── frontend/         # Aplicación Flutter (web / PWA)
    ├── lib/
    │   ├── config/   # api_config.dart (baseUrl desde --dart-define)
    │   ├── models/   # article.dart, evidence_level.dart, synthesis_result.dart
    │   ├── widgets/  # article_card.dart (badge de nivel), vocabulario_jerarquia_panel.dart
    │   └── screens/  # home_screen.dart, synthesis_screen.dart
    └── web/          # manifest.json + index.html de la PWA
```

---

## Inicio rápido

> [!TIP]
> **La app ya está publicada y funcionando:** https://jeronimopennini.github.io/EVIDENCIA/
> Con abrir ese link en Chrome ya podés probarla sin instalar nada (el primer
> llamado tarda ~1 minuto porque el plan free de Render despierta el backend).

### Opción A (más simple): probar en Chrome contra el backend público
Doble clic en `probar_en_nube.bat`. No requiere backend local: compila el
frontend apuntando a `https://evidencia-pljv.onrender.com` y abre Chrome.
La primera compilación tarda entre 40 y 90 segundos; parece congelado pero no lo está.

### Opción B: lanzador completo en 1 clic
* `iniciar_proyecto.bat`: abre el Backend local (puerto 8000) y el Frontend en dos ventanas.

Por separado: `iniciar_backend.bat` y `iniciar_frontend.bat`.

---

### Opción C: inicio manual desde terminales

> [!IMPORTANT]
> El backend es un servidor que **debe quedar corriendo de forma continua**. Por ello, requiere su propia terminal abierta. Para el frontend debés abrir una **segunda terminal**.

#### Terminal 1 — Backend (FastAPI):
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```
Documentación interactiva disponible en: http://localhost:8000/docs

#### Terminal 2 — Frontend (Flutter web):
```powershell
cd frontend
flutter run -d chrome
```

---

## Activar la síntesis por IA (Gemini)

La app funciona sin clave para buscar, pero la síntesis y la optimización de la query necesitan Gemini:

1. Pedí una clave gratuita en https://aistudio.google.com/app/apikey (nivel free, sin tarjeta).
2. En `backend/.env` reemplazá el placeholder: `GEMINI_API_KEY=AIza...`
3. Reiniciá el backend y revisá http://localhost:8000/health → `gemini_configurado` debería pasar a `true`.
4. En la app: buscá por PICO, seleccioná artículos y pulsá **Sintesis IA**. El prompt ya le pasa al modelo
   la jerarquía (ETS > RS/MA > ECA > observacionales) y la distribución por nivel, así que prioriza
   diseños de mayor calidad y avisa cuando la evidencia disponible es solo observacional.

Sin clave, el backend detecta que Gemini no está disponible, hace la traducción de términos con el
vocabulario controlado y la búsqueda por niveles, y desactiva la optimización IA automáticamente.

---

## Variables de entorno necesarias

| Variable | Descripción | Cómo obtenerla |
|---|---|---|
| `GEMINI_API_KEY` | Clave Google Gemini (gratuita). Necesaria para optimizar la query y generar la síntesis IA | https://aistudio.google.com/app/apikey |
| `GEMINI_MODEL` | Modelo usado (por defecto `gemini-3.5-flash`; si ya no está disponible el backend prueba respaldos) | — |
| `NCBI_API_KEY` | Clave NCBI (opcional, aumenta el rate limit de PubMed) | https://www.ncbi.nlm.nih.gov/account/ |
| `NCBI_EMAIL` | Email de contacto para NCBI | Tu email |
| `DECS_API_KEY` | Clave DeCS de BIREME/OPS (opcional). Sin ella se usa MeSH abierto de NLM | https://decs.bvsalud.org/ (licencia gratuita) |
| `DECS_API_BASE` | Endpoint DeCS (por defecto `https://api.bvsalud.org/decs/v2/`) | — |
| `BACKEND_PORT` / `PORT` | Puerto de escucha. `server_start.py` prioriza `PORT` (lo que inyecta Render/Railway/Docker) | — |
| `ALLOWED_ORIGINS` | Orígenes CORS separados por coma; en producción el dominio público del frontend | — |
| `CORS_ORIGIN_REGEX` | Regex extra de orígenes (default: cualquier puerto de localhost) | — |

> [!NOTE]
> Sin `GEMINI_API_KEY` la búsqueda sigue funcionando: se resuelve el vocabulario con el diccionario local + NLM MeSH Lookup y se busca por niveles en PubMed. Solo desactivá "Optimizar con IA" o dejá que el backend lo detecte solo.

---

## Vocabulario controlado DeCS / MeSH

`backend/app/services/decs_service.py` resuelve cada término PICO (español o inglés) contra vocabulario
controlado real, en cascada y con caché en `backend/data/vocab_cache.json` (30 días):

1. **API DeCS** (BIREME/OPS) si hay `DECS_API_KEY` → descriptor en español + su MeSH en inglés.
2. **Diccionario local** (`diccionario_es_en.py`) para términos clínicos y metodológicos frecuentes.
3. **NLM MeSH Lookup API** (sin clave) y **`db=mesh` de NCBI** para el descriptor canónico y su UID.

Con el descriptor se construye la cláusula PubMed (`"Diabetes Mellitus, Type 2"[MeSH Terms] OR ...[tiab]`)
y además `reparar_query()` corrige los descriptores inventados por la IA (p.ej.
`"type 2 diabetes"[MeSH Terms]`, que devuelve 0 resultados). El estado del vocabulario se ve en `/health`.

---

## Jerarquía de evidencia de calidad

`backend/app/services/evidence_service.py` busca y ordena por niveles, no solo por relevancia:

| Nivel | Diseño | Cómo se detecta en PubMed |
|---|---|---|
| 1 | **Evaluación de Tecnología Sanitaria (ETS/HTA)** | MeSH `Technology Assessment, Biomedical`, revistas HTA, agencias (NICE, INTA, CADTH…), frases de evaluación económica |
| 2 | **Revisiones sistemáticas y metaanálisis** | Publication Types `Systematic Review` / `Meta-Analysis` |
| 3 | **Ensayos clínicos aleatorizados (ECA)** | `Randomized Controlled Trial` + señales aleatorias no etiquetadas |
| 4 | **Observacionales de cohorte o casos y controles** | MeSH `Cohort Studies` / `Case-Control Studies`, `Observational Study[Filter]` |
| 5 | Otro diseño | transversales, series de casos, editoriales |

La búsqueda (`priorizar_calidad=true`) hace un `esearch` por nivel con cupos ponderados, deduplica entre
niveles y rellena el resto; cada artículo devuelve `nivel_evidencia`, `nivel_etiqueta`, `nivel_orden`
y `senal_nivel` (el metadato que justificó la clasificación). El frontend lo muestra como badge en la
tarjeta y como panel de cobertura por nivel.

---

## Endpoints API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio, IA configurada y estado del vocabulario |
| POST | `/api/v1/search` | Buscar artículos en PubMed (query libre) |
| POST | `/api/v1/search/pico` | PICO → vocabulario controlado → búsqueda por niveles |
| POST | `/api/v1/synthesize` | Síntesis IA priorizando los niveles de mayor calidad |

`/api/v1/search/pico` acepta además `usar_vocabulario_controlado`, `priorizar_calidad` y
`niveles` (subconjunto de `ets`, `rs_ma`, `rct`, `obs`), y devuelve `terminos_clinicos`,
`correcciones_vocabulario`, `niveles_consultados`, `totales_por_nivel` y `distribucion_devueltos`.

---

## Publicar: Web + PWA con backend en la nube

El mismo código Flutter compila para web (y se instala como PWA). La única pieza
nueva es un backend público con HTTPS, porque las claves API **nunca** viajan al cliente.

```
[ PWA: build/web ]  --HTTPS-->  [ FastAPI en Render/Railway ]  ---->  PubMed + Gemini
   hosting estático                  secreto GEMINI_API_KEY env
```

### 1. Backend público (Render free)

Opción blueprint (recomendada): `render.yaml` ya está en la raíz de este repo, así que en
Render elegí **New → Blueprint** y conectá `JeronimoPennini/EVIDENCIA`; te va a pedir los
valores de las variables marcadas `sync: false`. Opción manual, creando un *Web Service*:

| Campo | Valor |
|---|---|
| Repository | `JeronimoPennini/EVIDENCIA` (branch `main`) |
| Runtime | **Docker** |
| Dockerfile Path | `./Dockerfile` |
| Build Context Path | `/` (la raíz del repo) |
| Health Check Path | `/health` |

El `Dockerfile` vive en la raíz y usa rutas `backend/...` **porque el contexto de build es la
raíz del repo**. Si alguna vez ves `Exited with status 1 while building your code` en 40 s, casi
siempre es el Build Context mal puesto: el `COPY backend/requirements.txt` no encuentra nada.

Alternativa sin Docker (runtime Python): Root Directory `backend`, Build Command
`pip install -r requirements.txt`, Start Command `python server_start.py`.

En *Environment* cargá `GEMINI_API_KEY` (y opcionalmente `NCBI_API_KEY`, `DECS_API_KEY`) y
`ALLOWED_ORIGINS` con el dominio donde va a vivir el frontend. `server_start.py` lee el
`PORT` que inyecta el host y deja el keep-alive en 120 s para que la síntesis (~20-30 s) no
se corte.

Build local de la imagen (mismo contexto que usa Render): `docker build -t evidencia-api .`
desde la raíz del repo, y `docker run --rm -p 8000:8000 --env-file backend/.env evidencia-api`.
En Railway el Dockerfile se busca en la raíz del directorio de origen, así que o subís la raíz
con `railway up`, o apuntá `RAILWAY_DOCKERFILE_PATH` al `Dockerfile` del repo.

Cosas del plan gratuito de Render: el servicio **se duerme a los 15 minutos sin tráfico** y
despertar toma ~1 minuto → el primer pedido de la jornada falla o tarda. Si eso molesta, un ping
programado a `/health` lo mantiene despierto. La caché de vocabulario (`backend/data/`) es
efímera en contenedores: se reconstruye sola, sin clave ni volumen.

Chequear: `https://TU-BACKEND.onrender.com/health` → `gemini_configurado: true` y
`cors_origenes` con tu dominio.

### 2. Frontend (PWA en GitHub Pages)

Una sola vez: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
Después, `.github/workflows/web.yml` compila y publica solo con tocar `frontend/` (o con
*Actions → Run workflow*, indicando la URL del backend). El sitio queda en
`https://jeronimopennini.github.io/EVIDENCIA/`.

`--base-href /EVIDENCIA/` es obligatorio: es la subruta del project page, y coincide con la
que usa el workflow. Si cambiás el nombre del repo, actualizá el workflow y el `base-href`
local.

Para compilar a mano (o probar antes de mergear):

```powershell
.\build_web.bat https://TU-BACKEND.onrender.com     # deja frontend\build\web
```

Equivale a `flutter build web --release --dart-define=API_BASE_URL=https://TU-BACKEND.onrender.com`:
la URL pública entra en `frontend/lib/config/api_config.dart` (`ApiConfig.baseUrl`) sin tocar código;
sin el flag sigue usando `http://localhost:8000` para desarrollo. Para un build local destined
a Pages, agregá `--base-href /EVIDENCIA/`.

CORS: agregá `https://jeronimopennini.github.io` a `ALLOWED_ORIGINS` en Render (el
`render.yaml` del repo ya lo trae). HTTPS no es opcional: sin él el navegador no ofrece
*Instalar aplicación* ni registra el service worker; `web/manifest.json` ya declara nombre,
íconos y tema, así que se instala como app en Android/Chrome OS y en escritorio.

> [!WARNING]
> API publicada = API abierta: cualquiera que lea la URL puede gastar tu cuota gratuita de Gemini.
> Si dejás el enlace en circulación, poné un límite de gasto en AI Studio y revisá `/health` con frecuencia.

### 3. APK (cuando haga falta)

El mismo proyecto genera Android: `flutter create --platforms=android .` dentro de `frontend/`,
luego `flutter build apk --release --dart-define=API_BASE_URL=https://TU-BACKEND.onrender.com`.
Requiere backend público (punto 1) y permiso `INTERNET` en el manifest de Android.

---

## Tests

```powershell
cd backend
pip install -r requirements.txt   # incluye truststore, necesario para SSL en Windows
python -m pytest -q               # 58 tests; los marcados live consultan PubMed/MeSH reales

cd frontend
flutter test                      # smoke test + parseo/renderizado del vocabulario y la jerarquía
```

---

## Aviso ético

Las síntesis generadas por IA son herramientas de apoyo informativo.
**No reemplazan el juicio clínico profesional ni la lectura crítica de la literatura original.**
