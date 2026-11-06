"""Envoi du jour : une fois par jour, tout le quota du forfait part en un seul suivi.

L'essai envoie dix questions. Un forfait envoie les siennes d'un coup, jusqu'à deux cents
pour Référence. Si le client a déjà lancé le suivi aujourd'hui, il ne part pas une seconde fois.
"""

from __future__ import annotations

import asyncio
import logging

from seed import DEMO_EMAIL
from services.billing import quota_remaining
from services.orchestrator import run_tracking, tracking_plan
from services.progress import begin, snapshot
from store import store

logger = logging.getLogger(__name__)
# Un passage par heure suffit : le quota du jour empêche un second envoi.
INTERVAL = 60 * 60


def due_user_ids() -> list[str]:
    """Espaces qui ont encore des questions à envoyer aujourd'hui."""
    due: list[str] = []
    for user_id in store.workspace_user_ids():
        user = store.user_by_id(user_id)
        if user is None or user.email == DEMO_EMAIL:
            continue
        workspace = store.workspace_for(user_id)
        if workspace is None or not workspace.brand_name or not any(query.active for query in workspace.queries):
            continue
        try:
            remaining = quota_remaining(workspace)
        except (ValueError, KeyError):
            continue
        if remaining > 0:
            due.append(user_id)
    return due


async def send_due() -> int:
    """Lance le suivi du jour pour chaque espace encore dans son quota. Retourne le nombre de lancements."""
    started = 0
    for user_id in due_user_ids():
        if snapshot(user_id).running:
            continue
        try:
            _workspace, queries, _selected, steps = tracking_plan(user_id)
        except ValueError:
            continue
        if not queries:
            continue
        logger.info("Envoi du jour pour %s : %s questions d'un coup.", user_id, len(queries))
        begin(user_id, steps)
        try:
            await run_tracking(user_id, None, None, True)
        except Exception:
            logger.exception("Envoi du jour interrompu pour %s", user_id)
        started += 1
    return started


async def daily_loop() -> None:
    while True:
        try:
            await send_due()
        except Exception:
            logger.exception("Le passage du jour n'a pas abouti.")
        await asyncio.sleep(INTERVAL)
