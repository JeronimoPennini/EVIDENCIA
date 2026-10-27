# EvidencIA

> Aplicación de síntesis de evidencia científica en salud asistida por IA.
> Stack: **Flutter (web)** + **Python 3.14 / FastAPI** · Herramientas gratuitas.

---

## Estructura del proyecto

```
EvidencIA/
├── backend/          # API Python + FastAPI
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example  # Plantilla de claves (nunca versionar .env)
│   └── app/
│       ├── config.py
│       ├── models/
│       ├── routers/
│       └── services/
└── frontend/         # Aplicación Flutter (web)
    └── lib/
```

---

## Inicio rápido

### Opción A (Recomendada): Lanzador en 1 clic
Podés hacer doble clic en el archivo:
* `iniciar_proyecto.bat`: Abre automáticamente el Backend y el Frontend en dos ventanas independientes.

O si preferís ejecutarlos por separado con doble clic:
* `iniciar_backend.bat`
* `iniciar_frontend.bat`

---

### Opción B: Inicio manual desde terminales

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

## Variables de entorno necesarias

| Variable | Descripción | Cómo obtenerla |
|---|---|---|
| `NCBI_API_KEY` | Clave NCBI (opcional, aumenta rate limit) | https://www.ncbi.nlm.nih.gov/account/ |
| `NCBI_EMAIL` | Email de contacto para NCBI | Tu email |
| `GEMINI_API_KEY` | Clave Google Gemini (gratuita) | https://aistudio.google.com/app/apikey |

---

## Endpoints API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| POST | `/api/v1/search` | Buscar artículos en PubMed |
| POST | `/api/v1/synthesize` | Sintetizar evidencia con IA |

---

## Aviso ético

Las síntesis generadas por IA son herramientas de apoyo informativo.
**No reemplazan el juicio clínico profesional ni la lectura crítica de la literatura original.**
