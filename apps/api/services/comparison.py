from __future__ import annotations

from collections import defaultdict

from models.schemas import (
    CompareCell,
    CompareEntity,
    CompareGap,
    CompareHit,
    ComparePrompt,
    CompareProviderStat,
    CompareSource,
    ComparisonOut,
)
from services.analyzer import Entity, is_generic_platform, normalize_domain
from services.metrics import entities_of, measured_runs, run_mentions, week_start
from store import StoredRun, Workspace

def _method(span: str) -> str:
    window = "Semaine la plus récente uniquement." if span == "week" else "Toutes les réponses déjà enregistrées."
    return (
        f"{window} Visibilité : part des réponses où le nom apparaît. "
        "Position : rang moyen parmi les marques nommées, 1 étant la première. "
        "Sources propres : part des réponses qui citent le domaine de la marque. "
        "Réponses sourcées : part des réponses où le nom apparaît et où au moins une source est jointe. "
        "Aucun nouvel appel n'est lancé."
    )


def _owns(domain: str, entity: Entity) -> bool:
    owned = normalize_domain(entity.domain)
    if not owned:
        return False
    return domain == owned or domain.endswith(f".{owned}")


def _tone(value: float) -> str:
    if value >= 0.25:
        return "positive"
    if value <= -0.25:
        return "negative"
    return "neutral"


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def build_comparison(workspace: Workspace, span: str = "week", tag: str = "") -> ComparisonOut:
    entities = entities_of(workspace)
    brand = entities[0]
    completed = measured_runs(workspace)
    label = " ".join(tag.split())[:40]
    tags = sorted({item.tag.strip() for item in workspace.queries if item.tag.strip()}, key=str.casefold)
    if label:
        allowed = {item.id for item in workspace.queries if item.tag.strip().casefold() == label.casefold()}
        completed = [run for run in completed if run.query_id in allowed]
    latest = max((week_start(run.created_at) for run in completed), default=None)
    if span == "all":
        runs = list(completed)
    else:
        span = "week"
        runs = [run for run in completed if latest and week_start(run.created_at) == latest]
    prepared: list[tuple[StoredRun, dict[str, object]]] = []
    for run in runs:
        mentions = run_mentions(run, entities)
        prepared.append((run, {item.entity_name: item for item in mentions}))

    providers = list(dict.fromkeys(run.provider for run, _mentions in prepared))
    entity_rows = [_entity_row(entity, prepared, providers) for entity in entities]
    tags_by_query = {item.id: item.tag.strip() for item in workspace.queries}
    prompts = _prompts(entities, prepared, tags_by_query)
    sources = _sources(entities, brand, prepared)
    return ComparisonOut(
        brand_name=brand.name,
        domain=brand.domain,
        week=latest.date().isoformat() if latest else None,
        span="all" if span == "all" else "week",
        tags=tags,
        runs=len(prepared),
        providers=providers,  # type: ignore[arg-type]
        entities=entity_rows,
        prompts=prompts,
        sources=sources,
        gaps=_gaps(brand, entity_rows, prompts, sources, "sur la période" if span == "all" else "cette semaine"),
        methodology=_method(span),
    )


def _entity_row(entity: Entity, prepared: list[tuple[StoredRun, dict]], providers: list[str]) -> CompareEntity:
    total = len(prepared)
    mentions = []
    own_sources = 0
    sourced = 0
    by_provider: list[CompareProviderStat] = []
    for provider in providers:
        subset = [(run, found) for run, found in prepared if run.provider == provider]
        found_mentions = [found[entity.name] for _run, found in subset if entity.name in found]
        provider_sources = sum(1 for run, _found in subset if any(_owns(item.domain, entity) for item in run.citations))
        provider_sourced = sum(1 for run, found in subset if entity.name in found and run.citations)
        by_provider.append(
            CompareProviderStat(
                provider=provider,  # type: ignore[arg-type]
                runs=len(subset),
                mentions=len(found_mentions),
                visibility=round(len(found_mentions) / len(subset), 4) if subset else 0.0,
                average_position=_mean([item.position for item in found_mentions]),
                sentiment=_mean([item.sentiment for item in found_mentions]),
                own_source_rate=round(provider_sources / len(subset), 4) if subset else 0.0,
                sourced_rate=round(provider_sourced / len(subset), 4) if subset else 0.0,
            )
        )
    for run, found in prepared:
        mention = found.get(entity.name)
        if mention is not None:
            mentions.append(mention)
            if run.citations:
                sourced += 1
        if any(_owns(item.domain, entity) for item in run.citations):
            own_sources += 1
    tones = {"positive": 0, "neutral": 0, "negative": 0}
    for mention in mentions:
        tones[_tone(mention.sentiment)] += 1
    return CompareEntity(
        name=entity.name,
        domain=entity.domain,
        kind=entity.kind,  # type: ignore[arg-type]
        mentions=len(mentions),
        visibility=round(len(mentions) / total, 4) if total else 0.0,
        average_position=_mean([item.position for item in mentions]),
        sentiment=_mean([item.sentiment for item in mentions]),
        positive=tones["positive"],
        neutral=tones["neutral"],
        negative=tones["negative"],
        own_source_rate=round(own_sources / total, 4) if total else 0.0,
        sourced_rate=round(sourced / total, 4) if total else 0.0,
        by_provider=by_provider,
    )


def _prompts(entities: list[Entity], prepared: list[tuple[StoredRun, dict]], tags: dict[str, str]) -> list[ComparePrompt]:
    grouped: dict[str, list[tuple[StoredRun, dict]]] = defaultdict(list)
    for item in prepared:
        grouped[item[0].query_id].append(item)
    rows: list[ComparePrompt] = []
    for query_id, items in grouped.items():
        cells: list[CompareCell] = []
        for entity in entities:
            hits = [
                CompareHit(provider=run.provider, position=found[entity.name].position, sentiment=found[entity.name].sentiment)  # type: ignore[arg-type]
                for run, found in items
                if entity.name in found
            ]
            cells.append(CompareCell(name=entity.name, hits=hits))
        brand_hits = cells[0].hits if cells else []
        rows.append(
            ComparePrompt(
                query_id=query_id,
                prompt=items[0][0].query_prompt,
                tag=tags.get(query_id, ""),
                runs=len(items),
                brand_mentioned=bool(brand_hits),
                cells=cells,
            )
        )
    rows.sort(key=lambda item: (item.brand_mentioned, item.prompt.lower()))
    return rows


def _sources(entities: list[Entity], brand: Entity, prepared: list[tuple[StoredRun, dict]]) -> list[CompareSource]:
    bucket: dict[str, dict] = {}
    for run, found in prepared:
        seen: set[str] = set()
        named = [entity.name for entity in entities if entity.name in found]
        for citation in run.citations:
            domain = citation.domain
            if domain in seen or is_generic_platform("", domain):
                continue
            seen.add(domain)
            slot = bucket.setdefault(
                domain,
                {"citations": 0, "runs": 0, "with_brand": 0, "without_brand": 0, "entities": set()},
            )
            slot["citations"] += 1
            slot["runs"] += 1
            if brand.name in found or any(_owns(item.domain, brand) for item in run.citations):
                slot["with_brand"] += 1
            else:
                slot["without_brand"] += 1
            slot["entities"].update(named)
    rows: list[CompareSource] = []
    for domain, slot in bucket.items():
        owner = next((entity.name for entity in entities if _owns(domain, entity)), None)
        rows.append(
            CompareSource(
                domain=domain,
                citations=slot["citations"],
                runs=slot["runs"],
                runs_with_brand=slot["with_brand"],
                runs_without_brand=slot["without_brand"],
                owned_by=owner,
                entities=sorted(slot["entities"]),
            )
        )
    rows.sort(key=lambda item: (item.runs_without_brand, item.citations), reverse=True)
    return rows[:12]


def _gaps(
    brand: Entity,
    entities: list[CompareEntity],
    prompts: list[ComparePrompt],
    sources: list[CompareSource],
    period: str = "cette semaine",
) -> list[CompareGap]:
    gaps: list[CompareGap] = []
    ours = next((item for item in entities if item.name == brand.name), None)
    rivals = [item for item in entities if item.kind == "competitor"]
    missed = [item for item in prompts if not item.brand_mentioned and any(cell.hits for cell in item.cells[1:])]
    if missed:
        names = sorted({cell.name for prompt in missed for cell in prompt.cells[1:] if cell.hits})
        gaps.append(
            CompareGap(
                title=f"{len(missed)} question{'s' if len(missed) > 1 else ''} sans la marque",
                detail=(
                    f"{', '.join(names)} apparaissent là où {brand.name} n'est pas nommé. "
                    f"Première à traiter : « {missed[0].prompt} »."
                ),
            )
        )
    if ours and rivals:
        leader = max(rivals, key=lambda item: item.own_source_rate)
        if leader.own_source_rate > ours.own_source_rate:
            gaps.append(
                CompareGap(
                    title="Le domaine des concurrents est plus souvent une source",
                    detail=(
                        f"{leader.name} est cité comme source dans {round(leader.own_source_rate * 100)} % des réponses, "
                        f"{brand.name} dans {round(ours.own_source_rate * 100)} %. "
                        "Une page qui répond directement à la question augmente cette part."
                    ),
                )
            )
        happier = [item for item in rivals if item.sentiment is not None and ours.sentiment is not None and item.sentiment >= ours.sentiment + 0.2]
        if happier:
            best = max(happier, key=lambda item: item.sentiment or 0)
            gaps.append(
                CompareGap(
                    title="Le ton est plus favorable chez un concurrent",
                    detail=(
                        f"Le jugement moyen sur {best.name} est plus positif que sur {brand.name}. "
                        "Les pages doivent contenir des faits vérifiables, pas seulement un slogan."
                    ),
                )
            )
    external = next((item for item in sources if item.owned_by is None and item.runs_without_brand > 0), None)
    if external:
        gaps.append(
            CompareGap(
                title=f"{external.domain} est cité sans {brand.name}",
                detail=(
                    f"Ce domaine sert de source dans {external.runs_without_brand} réponse"
                    f"{'s' if external.runs_without_brand > 1 else ''} où {brand.name} est absent. "
                    "C'est l'endroit le plus utile pour obtenir une mention."
                ),
            )
        )
    if not gaps:
        gaps.append(
            CompareGap(
                title=f"Aucun écart net {period}",
                detail=f"{brand.name} est présente au moins aussi souvent que les concurrents suivis sur les questions mesurées.",
            )
        )
    return gaps[:4]
