"""
EvidencIA — Configuración central
Carga variables de entorno desde .env y las expone como settings tipados.
Las claves API NUNCA se serializan ni se envían al cliente.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # NCBI / PubMed
    ncbi_api_key: str = ""
    ncbi_email: str = "evidencia-app@localhost"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Servidor
    backend_port: int = 8000
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Retorna instancia singleton de Settings (cacheada)."""
    return Settings()
