from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-enterprise-playground"
    environment: str = "local"
    api_version: str = "v1"
    version: str = "0.1.0"

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "sqlite:///./app.db"
    chroma_persist_dir: str = "./data/chroma"
    uploads_dir: str = "./data/uploads"

    jwt_secret_key: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 14

    session_secret_key: str = "dev-session-secret"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
