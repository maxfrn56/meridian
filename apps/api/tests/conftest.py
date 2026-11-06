"""Les tests tournent sur une base SQLite jetable, jamais sur data/meridian.db."""

import os
import tempfile
from pathlib import Path

_DB_DIR = Path(tempfile.mkdtemp(prefix="meridian-tests-"))
# Doit être posé avant le premier import de config.
os.environ["DATABASE_URL"] = f"sqlite:///{(_DB_DIR / 'test.db').as_posix()}"
os.environ["DAILY_SEND"] = "false"

import pytest  # noqa: E402

import services.prospects  # noqa: E402
from db import engine, migrate  # noqa: E402

# Aucun test ne doit reprendre le data/prospects.json d'un développeur.
services.prospects.LEGACY_PATH = _DB_DIR / "absent.json"


@pytest.fixture(scope="session", autouse=True)
def database():
    migrate()
    yield
    engine.dispose()
