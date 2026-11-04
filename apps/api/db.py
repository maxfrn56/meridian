"""Connexion à la base : SQLite en local, PostgreSQL en production."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config import settings


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        database = url.split("///", 1)[-1]
        if database and database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record) -> None:  # pragma: no cover - plomberie SQLite
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Une transaction : commit si tout passe, rollback sinon."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def migrate() -> None:
    """Applique les migrations Alembic jusqu'à la dernière version."""
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.attributes["connection_url"] = settings.database_url
    # Laisser les logs d'uvicorn tranquilles.
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
