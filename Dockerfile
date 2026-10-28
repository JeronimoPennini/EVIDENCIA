# EvidencIA — imagen del backend FastAPI
#
# ⚠️ El contexto de build es la RAÍZ de este repo (así lo usa Render por defecto),
#    por eso todas las rutas van prefijadas con backend/.
#
# Build local:   docker build -t evidencia-api .
# Run local:     docker run --rm -p 8000:8000 --env-file backend/.env evidencia-api
# Render:        Web Service → Runtime Docker, Dockerfile Path ./Dockerfile,
#                Build Context Path / (raíz). Root Directory puede quedar vacío.
#
# Los secretos (GEMINI_API_KEY, NCBI_API_KEY, DECS_API_KEY, ALLOWED_ORIGINS)
# se inyectan como variables de entorno del host: nunca quedan en la imagen.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias primero: esta capa se reutiliza mientras no cambie requirements.txt
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Código: sólo el backend (frontend/ y .git quedan fuera por .dockerignore)
COPY backend/ ./backend/

# /app/backend/data es la caché de vocabulario: escribible, efímera
RUN useradd --create-home app \
    && mkdir -p /app/backend/data \
    && chown -R app:app /app
USER app

# Render/Railway definen PORT; 8000 es el default propio del proyecto
ENV PORT=8000
EXPOSE 8000

WORKDIR /app/backend

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:'+(os.environ.get('PORT') or '8000')+'/health', timeout=4)"

CMD ["python", "server_start.py"]
