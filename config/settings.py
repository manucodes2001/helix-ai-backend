"""Centralized immutable configuration management for Helix AI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


def load_environment(env_path: Path) -> None:
    """Load key=value pairs from .env without overriding already-set OS variables."""
    if not env_path.exists():
        return
    if load_dotenv is not None:
        load_dotenv(dotenv_path=env_path, override=False)
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_environment(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for Helix AI."""

    APP_NAME: str = "Helix AI"
    APP_FULL_NAME: str = "AI-Powered Scientific Research Agent"
    APP_CATEGORY: str = "Scientific Literature-to-Dataset Intelligence Platform"
    APP_VERSION: str = "1.0.0"

    PROJECT_ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    RAW_DATA_DIR: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "raw")
    PROCESSED_DATA_DIR: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "processed")
    BENCHMARK_DATA_DIR: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "benchmark")
    SCHEMA_PATH: Path = field(default_factory=lambda: PROJECT_ROOT / "database" / "schema.sql")

    DB_PATH: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "HELIX_DB_PATH",
                "/tmp/helix_ai.db" if os.getenv("VERCEL") else str(PROJECT_ROOT / "data" / "helix_ai.db"),
            )
        )
    )

    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip())
    OPENAI_BASE_URL: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "").strip())
    OPENAI_MODEL: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gemini-flash-lite-latest").strip())
    OPENAI_TEMPERATURE: float = 0.0
    OPENAI_MAX_TOKENS: int = 2000

    NCBI_API_KEY: str = field(default_factory=lambda: os.getenv("NCBI_API_KEY", "").strip())
    NCBI_EMAIL: str = field(default_factory=lambda: os.getenv("NCBI_EMAIL", "researcher@helix-ai.org").strip())
    NCBI_TOOL: str = "helix-ai"
    NCBI_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    NCBI_MAX_RETRIES: int = 3
    NCBI_BACKOFF_FACTOR: float = 1.5
    NCBI_TIMEOUT_SEC: int = 20
    CACHE_TTL_HOURS: int = 72

    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").strip().upper())

    @property
    def ncbi_rate_limit_per_sec(self) -> float:
        return 10.0 if self.has_ncbi_key else 3.0

    @property
    def has_openai_key(self) -> bool:
        return bool(self.OPENAI_API_KEY) and self.OPENAI_API_KEY != "your_openai_api_key_here"

    @property
    def has_ncbi_key(self) -> bool:
        return bool(self.NCBI_API_KEY) and self.NCBI_API_KEY != "your_ncbi_api_key_here"


def get_settings() -> Settings:
    return Settings()
