"""
EvidencIA — Configuración central
Carga variables de entorno desde .env y las expone como settings tipados.
Las claves API NUNCA se serializan ni se envían al cliente.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # NCBI / PubMed
    ncbi_api_key: str = ""
    ncbi_email: str = "evidencia-app@localhost"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    # Vocabulario controlado DeCS (BIREME/OPS). Sin clave se usa MeSH abierto (NLM/NCBI).
    decs_api_key: str = ""
    decs_api_base: str = "https://api.bvsalud.org/decs/v2/"

    # Búsqueda
    priorizar_calidad_por_defecto: bool = True

    # Servidor
    # En hosting (Render / Railway / Docker) el puerto llega en PORT; en local
    # se puede sobreescribir con BACKEND_PORT.
    backend_port: int = Field(
        default=8000,
        validation_alias=AliasChoices("BACKEND_PORT", "PORT"),
    )
    # Orígenes permitidos para CORS, separados por coma. Para el despliegue web
    # agregá acá el dominio público del frontend, p.ej.:
    #   ALLOWED_ORIGINS=https://evidencia.app,https://usuario.github.io
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"
    # Regex de orígenes: por defecto deja pasar cualquier puerto de localhost
    # (Flutter web usa puertos efímeros). Poner "" para desactivarla.
    cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def origins_abiertos(self) -> bool:
        """True si se declaró '*' (cualquier origen puede llamar a la API)."""
        return "*" in self.origins_list

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Retorna instancia singleton de Settings (cacheada)."""
    return Settings()
