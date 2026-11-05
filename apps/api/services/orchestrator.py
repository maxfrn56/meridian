from __future__ import annotations

import uuid
from datetime import datetime, timezone
from services.auditor import crawl_site
from services.billing import assert_quota
from services.llm_analysis import analysis_version, analyze_runs
from services.metrics import entities_of
from services.tracker import PROVIDERS, execute_batch
from store import StoredAudit, StoredRun, store


async def run_tracking(
    user_id: str,
    query_ids: list[str] | None = None,
    providers: list[str] | None = None,
) -> int:
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
    assert_quota(workspace, len(queries))
    # La marque, plus les concurrents déjà repérés : Claude écrira leurs noms de la même façon d'une réponse à l'autre.
    entities = entities_of(workspace)
    jobs = [(query.id, query.prompt, provider) for query in queries for provider in selected]
    prompts = {query.id: query.prompt for query in queries}
    results = await execute_batch(jobs, entities)
    stored: list[StoredRun] = []
    for query_id, provider, text, citations, model, source_mode, error, created_at in results:
        stored.append(
            StoredRun(
                id=uuid.uuid4().hex,
                query_id=query_id,
                query_prompt=prompts[query_id],
                provider=provider,
                model=model,
                status="failed" if error else "completed",
                source=source_mode,
                response_text=text,
                citations=citations,
                error=error,
                created_at=created_at,
            )
        )
    analyses = await analyze_runs(stored, entities)
    version = analysis_version()
    for run in stored:
        if run.id in analyses:
            run.analysis = analyses[run.id]
            run.analysis_version = version
    store.add_runs(user_id, stored)
    store.consume_questions(user_id, len(queries))
    return len(stored)


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
