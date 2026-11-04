from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_root = Path(__file__).resolve().parents[2]
_load_env_file(_root / ".env")
_load_env_file(Path(__file__).resolve().parent / ".env")


def _flag(name: str, default: str) -> str:
    return os.getenv(name, default).strip().lower()


@dataclass(frozen=True)
class Settings:
    secret_key: str
    openai_api_key: str
    perplexity_api_key: str
    gemini_api_key: str
    mock_llm: str
    redis_url: str
    async_tasks: bool
    use_playwright: bool
    allowed_origins: tuple[str, ...]
    database_url: str
    seed_demo: bool

    def provider_mode(self, provider: str) -> str:
        """live si la clé existe et que la simulation n'est pas forcée."""
        key = {
            "openai": self.openai_api_key,
            "perplexity": self.perplexity_api_key,
            "gemini": self.gemini_api_key,
        }.get(provider, "")
        if self.mock_llm == "true":
            return "mock"
        if self.mock_llm == "false":
            return "live"
        return "live" if key else "mock"


_DEFAULT_DB = Path(__file__).resolve().parent / "data" / "meridian.db"


def database_url_from_env() -> str:
    """URL SQLAlchemy. SQLite par défaut en local, Postgres quand DATABASE_URL est posé.

    Railway et Heroku donnent postgres:// ou postgresql:// : on force le pilote psycopg 3.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{_DEFAULT_DB.as_posix()}"
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def load_settings() -> Settings:
    origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return Settings(
        secret_key=os.getenv("GEO_SECRET", "dev-meridian-secret"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        mock_llm=_flag("MOCK_LLM", "auto"),
        redis_url=os.getenv("REDIS_URL", ""),
        async_tasks=_flag("ASYNC_TASKS", "false") in {"1", "true", "yes"},
        use_playwright=_flag("USE_PLAYWRIGHT", "false") in {"1", "true", "yes"},
        allowed_origins=tuple(part.strip() for part in origins.split(",") if part.strip()),
        database_url=database_url_from_env(),
        seed_demo=_flag("SEED_DEMO", "true") in {"1", "true", "yes"},
    )


settings = load_settings()
