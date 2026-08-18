from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment variables / .env.

    Kept intentionally small during Phase 1 (application shell) — grows as
    later phases (dataset ingestion, storage, worker) come online.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NeuroSleep Twin API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg2://neurosleep:neurosleep@localhost:5432/neurosleep"
    redis_url: str = "redis://localhost:6379/0"

    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "neurosleep-twin"
    object_storage_access_key: str = ""
    object_storage_secret_key: str = ""

    # Research Assistant (Phase 15). With both providers unset, the assistant
    # falls back to template-based narration of the same structured context
    # it would otherwise hand to a model. Ollama is checked first (it's
    # local, no key needed) — set ollama_model to "" to skip it even if a
    # server is running locally.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    # Bearer token required on every request except /health when set (README
    # §11/§18). Empty by default so a fresh clone still runs locally without
    # extra setup — set this before exposing the API beyond localhost.
    api_auth_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
