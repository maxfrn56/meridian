from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from services.auditor import crawl_site
from services.billing import assert_quota, quota_remaining
from services.llm_analysis import analysis_version, analyze_runs
from services import progress
from services.metrics import entities_of
from services.tracker import PROVIDERS, execute_batch
from store import StoredAudit, StoredRun, store

ENGINE_LABELS = {
    "openai": "ChatGPT",
    "google_ai_overview": "Google AI Overviews",
    "google_ai_mode": "Google AI Mode",
    "gemini": "Gemini",
    "perplexity": "Perplexity",
    "claude": "Claude",
    "aistudio": "Google AI Studio",
}


def tracking_plan(
    user_id: str,
    query_ids: list[str] | None = None,
    providers: list[str] | None = None,
):
    """Questions actives et modèles choisis. Lève ValueError si le suivi ne peut pas partir."""
    workspace = store.workspace_for(user_id)
    if workspace is None:
        raise ValueError("Espace introuvable.")
    selected = list(providers) if providers else list(workspace.providers)
    unknown = [item for item in selected if item not in PROVIDERS]
    if unknown:
        raise ValueError(f"Moteur inconnu : {', '.join(unknown)}.")
    queries = workspace.queries
    if query_ids is not None:
        wanted = set(query_ids)
        queries = [query for query in queries if query.id in wanted]
    else:
        queries = [query for query in queries if query.active]
    if not queries:
        raise ValueError("Aucune requête active à envoyer.")
    if not workspace.brand_name:
        raise ValueError("Renseignez le nom de la marque avant de lancer un suivi.")
    # L'ordre des réglages est l'ordre de pertinence : le quota du jour est dépensé en partant du haut.
    remaining = quota_remaining(workspace)
    if remaining < len(queries):
        if remaining <= 0:
            assert_quota(workspace, len(queries))
        queries = queries[:remaining]
    # Une étape de lecture par question, en plus de chaque envoi.
    steps = len(queries) * (len(selected) + 1)
    return workspace, queries, selected, steps


def _short(prompt: str) -> str:
    text = " ".join(prompt.split())
    if len(text) > 72:
        return text[:69].rstrip() + "…"
    return text


async def run_tracking(
    user_id: str,
    query_ids: list[str] | None = None,
    providers: list[str] | None = None,
    started: bool = False,
) -> int:
    """Envoie chaque question, l'enregistre et la compte avant de passer à la suivante.

    Un long suivi ne tient pas dans une seule requête HTTP : la réponse est renvoyée
    tout de suite, et ce travail continue. Chaque question déjà reçue reste en base
    même si la suite est interrompue.
    """
    error = ""
    try:
        workspace, queries, selected, steps = tracking_plan(user_id, query_ids, providers)
        if not started:
            progress.begin(user_id, steps)
        # La marque, plus les concurrents déjà repérés : Claude écrira leurs noms de la même façon d'une réponse à l'autre.
        entities = entities_of(workspace)
        prompts = {query.id: query.prompt for query in queries}
        expected = {query.id: len(selected) for query in queries}
        pending: dict[str, list] = {query.id: [] for query in queries}
        saved = 0
        lock = asyncio.Lock()

        async def on_result(row, prompt: str) -> None:
            nonlocal saved
            query_id = row.query_id
            provider = row.provider
            progress.advance(user_id, f"{ENGINE_LABELS.get(provider, provider)} · {_short(prompt)}")
            async with lock:
                bucket = pending.get(query_id)
                if bucket is None:
                    return
                bucket.append(row)
                ready = len(bucket) >= expected[query_id]
                rows = list(bucket) if ready else None
                if ready:
                    pending.pop(query_id, None)
            if rows is None:
                return
            stored = [
                StoredRun(
                    id=uuid.uuid4().hex,
                    query_id=query_id,
                    query_prompt=prompts[query_id],
                    provider=item.provider,
                    model=item.model,
                    status=item.status,
                    source=item.source_mode,
                    response_text=item.text,
                    citations=item.citations,
                    error=item.error,
                    created_at=item.created_at,
                )
                for item in rows
            ]
            progress.retitle(user_id, "Lecture des réponses…")
            analyses = await analyze_runs(stored, entities)
            version = analysis_version()
            for run in stored:
                if run.id in analyses:
                    run.analysis = analyses[run.id]
                    run.analysis_version = version
            store.add_runs(user_id, stored)
            store.consume_questions(user_id, 1)
            saved += 1
            progress.advance(user_id, "Lecture des réponses…")

        jobs = [(query.id, query.prompt, provider) for query in queries for provider in selected]
        await execute_batch(jobs, entities, on_result=on_result)
        return saved
    except Exception as exc:
        error = str(exc) if isinstance(exc, ValueError) else "Le suivi s'est interrompu. Les questions déjà envoyées sont conservées."
        raise
    finally:
        progress.finish(user_id, error)


async def run_audit(user_id: str, url: str | None = None) -> None:
    workspace = store.workspace_for(user_id)
    if workspace is None:
        raise ValueError("Espace introuvable.")
    target = (url or workspace.domain or "").strip()
    if not target:
        raise ValueError("Renseignez un domaine à auditer.")
    if "://" not in target:
        target = f"https://{target}"
    draft = await crawl_site(target)
    store.add_audit(
        user_id,
        StoredAudit(id=uuid.uuid4().hex, draft=draft, created_at=datetime.now(timezone.utc)),
    )
