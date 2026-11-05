from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from config import ENGINES
from services.analyzer import Citation, Entity, host_of
from services.llm import complete
from services.simulator import Source

PROVIDERS = ENGINES
# Choix par défaut d'un espace : trois moteurs parmi le catalogue (le client peut les changer).
DEFAULT_PROVIDERS = ("openai", "perplexity", "gemini")
# Questions envoyées en même temps à un même moteur (DataForSEO accepte 30 tâches live par plateforme).
PER_ENGINE = 5


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


@dataclass(frozen=True)
class BatchResult:
    query_id: str
    provider: str
    text: str
    citations: list[Citation]
    model: str
    source_mode: str
    error: str | None
    created_at: datetime
    no_answer: bool = False

    @property
    def status(self) -> str:
        if self.error:
            return "failed"
        return "no_answer" if self.no_answer else "completed"


async def execute_batch(
    jobs: list[tuple[str, str, str]],
    entities: list[Entity],
    on_done=None,
    on_result=None,
) -> list[BatchResult]:
    """jobs: (query_id, prompt, provider).

    Chaque question est envoyée telle quelle, sans y injecter la marque : le taux de citation ne veut
    dire quelque chose que si le prompt reste celui que l'utilisateur a défini.
    Une file par moteur : un moteur lent ou limité ne retient pas les autres.
    on_done(provider, prompt) et on_result(result, prompt) sont appelés après chaque réponse,
    une fois le créneau libéré. on_result peut être asynchrone.
    """
    semaphores = {provider: asyncio.Semaphore(PER_ENGINE) for _query_id, _prompt, provider in jobs}
    created_at = datetime.now(timezone.utc)

    async def one(query_id: str, prompt: str, provider: str) -> BatchResult:
        async with semaphores[provider]:
            answer = await complete(provider, prompt, entities, f"{query_id}|{created_at.isoformat()}")
        result = BatchResult(
            query_id=query_id,
            provider=provider,
            text=answer.text,
            citations=citations_from_sources(answer.sources),
            model=answer.model,
            source_mode=answer.source_mode,
            error=answer.error,
            created_at=created_at,
            no_answer=answer.no_answer,
        )
        if on_done is not None:
            on_done(provider, prompt)
        if on_result is not None:
            outcome = on_result(result, prompt)
            if hasattr(outcome, "__await__"):
                await outcome
        return result

    return await asyncio.gather(*(one(query_id, prompt, provider) for query_id, prompt, provider in jobs))
