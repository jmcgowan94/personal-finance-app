"""Application settings, read from environment variables (and an optional .env file).

Everything that differs between a laptop and AWS lives here, so the same code and
container image run in both places.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"), extra="ignore"
    )

    # SQLite by default so a fresh clone runs with no extra services.
    # docker compose / AWS set this to a Postgres URL.
    database_url: str = f"sqlite:///{DATA_DIR / 'app.db'}"

    # "local": every request is the single local user (no login).
    # "cognito": requests must carry a Cognito JWT (used once hosted on AWS).
    auth_mode: Literal["local", "cognito"] = "local"
    local_user_subject: str = "local"
    cognito_region: str | None = None
    cognito_user_pool_id: str | None = None
    cognito_app_client_id: str | None = None

    # Where raw uploaded CSVs are kept.
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: Path = DATA_DIR / "uploads"
    s3_bucket: str | None = None

    # Comma-separated list of origins allowed to call the API.
    cors_origins: str = "http://localhost:5173"
    max_upload_bytes: int = 10 * 1024 * 1024

    @model_validator(mode="after")
    def _resolve_relative_paths(self) -> "Settings":
        # Relative paths are relative to the repo root, wherever the app is started from.
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            path = self.database_url[len(prefix):]
            if path and path != ":memory:" and not Path(path).is_absolute():
                self.database_url = prefix + str(REPO_ROOT / path)
        if not self.local_storage_dir.is_absolute():
            self.local_storage_dir = REPO_ROOT / self.local_storage_dir
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
