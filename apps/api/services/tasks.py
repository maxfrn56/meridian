"""File Celery optionnelle.

Le MVP exécute le suivi dans le process FastAPI, car les runs vivent en mémoire.
Activez Celery seulement quand PostgreSQL est la source de vérité partagée
entre l'API et les workers : un process séparé ne voit pas le store mémoire.

    celery -A services.tasks:celery_app worker --loglevel=info
"""

from __future__ import annotations

import os

from config import settings


def _build():
    from celery import Celery

    broker = settings.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
    app = Celery("geo", broker=broker, backend=broker)
    app.conf.update(task_always_eager=not settings.async_tasks, task_ignore_result=False)
    return app


def get_celery():
    return _build()


try:
    celery_app = get_celery()
except ImportError:  # pragma: no cover - celery absent
    celery_app = None


if celery_app is not None:

    @celery_app.task(name="geo.tracking.run")
    def run_tracking_task(user_id: str, query_ids: list[str] | None, providers: list[str] | None) -> dict:
        # Import tardif pour éviter un cycle au chargement de l'API.
        import asyncio

        from services.orchestrator import run_tracking

        created = asyncio.run(run_tracking(user_id, query_ids, providers))
        return {"created": created}
