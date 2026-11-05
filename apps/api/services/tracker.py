from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from services.analyzer import Citation, Entity, host_of
from services.llm import complete
from services.simulator import Source

PROVIDERS = ("openai", "perplexity", "gemini", "claude", "aistudio")
DEFAULT_PROVIDERS = ("openai", "perplexity", "gemini")


def entities_from_workspace(brand_name: str, domain: str) -> list[Entity]:
    return [Entity(name=brand_name, domain=domain, kind="brand")]


def citations_from_sources(sources: list[Source]) -> list[Citation]:
    citations: list[Citation] = []
    for position, source in enumerate(sources, start=1):
        citations.append(
            Citation(
                url=source.url,
                domain=host_of(source.url),
                title=source.title,
                position=position,
            )
        )
    return citations


async def execute_query(
    prompt: str,
    provider: str,
    entities: list[Entity],
    nonce: str,
) -> tuple[str, list[Citation], str, str, str | None]:
    """Envoie la requête telle quelle, sans y injecter la marque.

    Le taux de citation ne veut dire quelque chose que si le prompt reste celui
    que l'utilisateur a défini.
    """
    result = await complete(provider, prompt, entities, nonce)
    return result.text, citations_from_sources(result.sources), result.model, result.source_mode, result.error


async def execute_batch(
    jobs: list[tuple[str, str, str]],
    entities: list[Entity],
) -> list[tuple[str, str, str, list[Citation], str, str, str | None, datetime]]:
    """jobs: (query_id, prompt, provider)."""
    semaphore = asyncio.Semaphore(4)
    created_at = datetime.now(timezone.utc)

    async def one(query_id: str, prompt: str, provider: str):
        async with semaphore:
            text, citations, model, source_mode, error = await execute_query(
                prompt, provider, entities, nonce=f"{query_id}|{created_at.isoformat()}"
            )
            return query_id, provider, text, citations, model, source_mode, error, created_at

    return await asyncio.gather(*(one(query_id, prompt, provider) for query_id, prompt, provider in jobs))
