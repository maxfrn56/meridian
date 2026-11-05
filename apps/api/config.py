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


# Moteurs suivis, dans l'ordre d'affichage. « openai » reste l'identifiant de ChatGPT : l'historique y est rattaché.
ENGINES = ("openai", "google_ai_overview", "google_ai_mode", "gemini", "perplexity", "claude")
# Moteurs que DataForSEO sait interroger ; les autres n'ont qu'un appel direct, avec leur propre clé.
DATAFORSEO_ENGINES = frozenset(ENGINES)


def _engines(raw: str) -> tuple[str, ...]:
    wanted = [part.strip().lower() for part in raw.split(",") if part.strip()]
    chosen = tuple(engine for engine in ENGINES if engine in wanted)
    return chosen or ENGINES


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
    anthropic_api_key: str
    analysis_model: str
    analysis_llm: str
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    # Pays des réponses (moteurs et recherche web) et langue par défaut si la question ne la trahit pas.
    dataforseo_country: str = "FR"
    dataforseo_language: str = "fr"
    claude_model: str = "claude-sonnet-5-5"
    perplexity_model: str = "sonar"
    engines: tuple[str, ...] = ENGINES

    def provider_backend(self, provider: str) -> str | None:
        """dataforseo si ses identifiants sont posés, sinon l'API directe si sa clé existe, sinon rien."""
        if self.dataforseo_login and self.dataforseo_password and provider in DATAFORSEO_ENGINES:
            return "dataforseo"
        key = {
            "openai": self.openai_api_key,
            "perplexity": self.perplexity_api_key,
            "gemini": self.gemini_api_key,
        }.get(provider, "")
        return "direct" if key else None

    def provider_mode(self, provider: str) -> str:
        """live si le moteur peut être interrogé et que la simulation n'est pas forcée."""
        if self.mock_llm == "true":
            return "mock"
        if self.mock_llm == "false":
            return "live"
        return "live" if self.provider_backend(provider) else "mock"

    def llm_analysis_enabled(self) -> bool:
        """Analyse des réponses par Claude : active dès que la clé existe, sauf ANALYSIS_LLM=false."""
        return bool(self.anthropic_api_key) and self.analysis_llm != "false"


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
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        analysis_model=os.getenv("ANALYSIS_MODEL", "claude-haiku-5-5").strip() or "claude-haiku-5-5",
        analysis_llm=_flag("ANALYSIS_LLM", "auto"),
        dataforseo_login=os.getenv("DATAFORSEO_LOGIN", "").strip(),
        dataforseo_password=os.getenv("DATAFORSEO_PASSWORD", "").strip(),
        dataforseo_country=(os.getenv("DATAFORSEO_COUNTRY", "FR").strip() or "FR").upper(),
        dataforseo_language=(os.getenv("DATAFORSEO_LANGUAGE", "fr").strip() or "fr").lower(),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5").strip() or "claude-sonnet-5-5",
        perplexity_model=os.getenv("PERPLEXITY_MODEL", "sonar").strip() or "sonar",
        engines=_engines(os.getenv("ENGINES", "")),
    )


settings = load_settings()
