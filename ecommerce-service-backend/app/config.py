from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Environment variables take precedence over the private local file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def required_database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required; copy .env.example to .env and configure it.")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = required_database_url()
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "18081"))


settings = Settings()
