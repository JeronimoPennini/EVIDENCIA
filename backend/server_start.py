"""
EvidencIA — Arranque del servidor para hosting (Render / Railway / Docker).

Leé el puerto desde el entorno (PORT, que inyectan los proveedores; o
BACKEND_PORT para local) y corre uvicorn sin reload ni workers extra: el plan
gratuito da ~512 MB y una sola instancia, así que se deja que el orquestador
escale si hace falta.

    python server_start.py          # escucha en 0.0.0.0:$PORT
    uvicorn main:app --reload       # sigue siendo válido para desarrollo
"""

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        log_level="info",
        # La síntesis por IA tarda ~20-30 s; keep-alive largo evita que el proxy
        # cierre la conexión antes de que llegue la respuesta.
        timeout_keep_alive=120,
        timeout_graceful_shutdown=10,
    )


if __name__ == "__main__":
    main()
