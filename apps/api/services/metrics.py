from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from config import settings
from models.schemas import (
    AuditHistoryPoint,
    AuditOut,
    AuditResponse,
    DiscoveredCompetitor,
    CheckOut,
    CitationOut,
    DomainStat,
    Kpis,
    MentionOut,
    OverviewOut,
    QueryTrackingOut,
    RecommendationOut,
    SovSlice,
    TrackingOut,
    TrackingRunOut,
    TrendPoint,
)
from services.analyzer import (
    Entity,
    brand_is_cited,
    citation_rate,
    Mention,
    extract_mentions,
    fold,
    is_generic_platform,
    matching_entity,
    mentions_from_analysis,
    named_organisations,
    normalize_domain,
    share_of_voice,
)
from services.llm import redact_secrets
from services.recommender import DomainGap, build_recommendations
from store import StoredAudit, StoredRun, Workspace

METHODOLOGY = (
    "Taux de citation : part des réponses où la marque est nommée ou dont le domaine apparaît dans les sources. "
    "Part de voix : mentions de la marque rapportées à celles des marques les plus citées à ses côtés, une fois par réponse. "
    "Les réponses réelles sont lues par Claude (marques nommées, rang, ton) ; à défaut, par mots-clés."
)


def run_mentions(run: StoredRun, entities: list[Entity]) -> list[Mention]:
    """Mentions des marques suivies : analyse LLM enregistrée si elle existe, sinon mots-clés."""
    if run.analysis is not None:
        return mentions_from_analysis(run.response_text, run.analysis, entities)
    return extract_mentions(run.response_text, entities)


# Concurrents retenus pour la part de voix et le comparatif : les plus cités par les moteurs.
MAX_RIVALS = 5


@dataclass(frozen=True)
class Rival:
    name: str
    domain: str
    mentions: int
    providers: tuple[str, ...]


def _named_brands(run: StoredRun) -> list[tuple[str, str]]:
    """Marques nommées dans une réponse : analyse LLM si elle existe, sinon les « Nom (domaine) » du texte."""
    if run.analysis is not None:
        return [(item.name, item.domain) for item in run.analysis]
    return named_organisations(run.response_text)


def market_rivals(workspace: Workspace) -> list[Rival]:
    """Les concurrents ne sont pas déclarés : ce sont les marques que les moteurs nomment avec ou à la place du client.

    Classées par nombre de réponses qui les nomment, toutes questions et tous moteurs confondus.
    """
    brand = [Entity(workspace.brand_name, workspace.domain, "brand")]
    counts: dict[str, int] = defaultdict(int)
    names: dict[str, str] = {}
    domains: dict[str, str] = {}
    providers: dict[str, set[str]] = defaultdict(set)
    for run in _completed(workspace):
        seen: set[str] = set()
        for name, domain in _named_brands(run):
            key = fold(name)
            if not key or key in seen or matching_entity(name, domain, brand) is not None:
                continue
            if is_generic_platform(name, domain):
                continue
            seen.add(key)
            counts[key] += 1
            names.setdefault(key, name)
            if domain and not domains.get(key):
                domains[key] = normalize_domain(domain)
            providers[key].add(run.provider)
    ranked = sorted(counts, key=lambda key: (-counts[key], names[key].lower()))
    return [
        Rival(name=names[key], domain=domains.get(key, ""), mentions=counts[key], providers=tuple(sorted(providers[key])))
        for key in ranked
    ]


def entities_of(workspace: Workspace) -> list[Entity]:
    entities = [Entity(workspace.brand_name, workspace.domain, "brand")]
    entities.extend(Entity(item.name, item.domain, "competitor") for item in market_rivals(workspace)[:MAX_RIVALS])
    return entities


def week_start(value: datetime) -> datetime:
    day = value.astimezone(timezone.utc).date()
    monday = day - timedelta(days=day.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


def _tracked_domains(entities: list[Entity]) -> set[str]:
    return {normalize_domain(entity.domain) for entity in entities if entity.domain}


def _is_tracked(domain: str, tracked: set[str]) -> bool:
    return any(domain == item or domain.endswith(f".{item}") for item in tracked if item)


def project_run(run: StoredRun, entities: list[Entity]) -> TrackingRunOut:
    mentions = run_mentions(run, entities) if run.status == "completed" else []
    brand = entities[0]
    cited = brand_is_cited(mentions, run.citations, brand) if run.status == "completed" else False
    brand_mention = next((item for item in mentions if item.entity_type == "brand"), None)
    return TrackingRunOut(
        id=run.id,
        query_id=run.query_id,
        query_prompt=run.query_prompt,
        provider=run.provider,  # type: ignore[arg-type]
        model=run.model,
        status=run.status,  # type: ignore[arg-type]
        source=run.source,  # type: ignore[arg-type]
        cited=cited,
        position=brand_mention.position if brand_mention else None,
        sentiment=brand_mention.sentiment if brand_mention else None,
        error=redact_secrets(run.error) if run.error else None,
        response_text=run.response_text,
        citations=[
            CitationOut(url=item.url, domain=item.domain, title=item.title, position=item.position)
            for item in run.citations
        ],
        analysis="llm" if run.analysis is not None else "keywords",
        mentions=[
            MentionOut(
                entity_name=item.entity_name,
                entity_type=item.entity_type,  # type: ignore[arg-type]
                position=item.position,
                sentiment=item.sentiment,
                excerpt=item.excerpt,
                stance=item.stance,  # type: ignore[arg-type]
            )
            for item in mentions
        ],
        created_at=run.created_at,
    )


def _completed(workspace: Workspace) -> list[StoredRun]:
    return [run for run in workspace.runs if run.status == "completed"]


def llm_mode(workspace: Workspace) -> str:
    completed = _completed(workspace)
    if not completed:
        modes = {settings.provider_mode(provider) for provider in workspace.providers}
    else:
        latest = max(run.created_at for run in completed).date()
        modes = {run.source for run in completed if run.created_at.date() == latest}
    if modes == {"mock"}:
        return "mock"
    if modes == {"live"}:
        return "live"
    return "mixed"


def domain_gaps(workspace: Workspace) -> list[DomainGap]:
    entities = entities_of(workspace)
    tracked = _tracked_domains(entities)
    brand = entities[0]
    citations: dict[str, int] = defaultdict(int)
    missing: dict[str, int] = defaultdict(int)
    for run in _completed(workspace):
        mentions = run_mentions(run, entities)
        cited = brand_is_cited(mentions, run.citations, brand)
        seen: set[str] = set()
        for citation in run.citations:
            if _is_tracked(citation.domain, tracked) or citation.domain in seen or is_generic_platform("", citation.domain):
                continue
            seen.add(citation.domain)
            citations[citation.domain] += 1
            if not cited:
                missing[citation.domain] += 1
    return [
        DomainGap(domain=domain, citations=count, runs_without_brand=missing[domain])
        for domain, count in citations.items()
    ]


def _sov_for(runs: list[StoredRun], entities: list[Entity]) -> tuple[dict[str, float], dict[str, int]]:
    counts = {entity.name: 0 for entity in entities}
    for run in runs:
        seen: set[str] = set()
        for mention in run_mentions(run, entities):
            if mention.entity_name in seen:
                continue
            seen.add(mention.entity_name)
            counts[mention.entity_name] = counts.get(mention.entity_name, 0) + 1
    return share_of_voice(counts), counts


def build_overview(workspace: Workspace) -> OverviewOut:
    entities = entities_of(workspace)
    brand = entities[0]
    completed = _completed(workspace)
    by_week: dict[datetime, list[StoredRun]] = defaultdict(list)
    for run in completed:
        by_week[week_start(run.created_at)].append(run)
    audits_by_week: dict[datetime, StoredAudit] = {}
    for audit in workspace.audits:
        audits_by_week[week_start(audit.created_at)] = audit

    trend: list[TrendPoint] = []
    for week in sorted(set(by_week) | set(audits_by_week)):
        runs = by_week.get(week, [])
        flags = []
        for run in runs:
            mentions = run_mentions(run, entities)
            flags.append(brand_is_cited(mentions, run.citations, brand))
        rate = citation_rate(flags) if flags else 0.0
        shares, _counts = _sov_for(runs, entities) if runs else ({brand.name: 0.0}, {})
        audit = audits_by_week.get(week)
        trend.append(
            TrendPoint(
                week=week.date().isoformat(),
                citation_rate=rate or 0.0,
                share_of_voice=shares.get(brand.name, 0.0),
                geo_score=audit.draft.score if audit else None,
            )
        )

    latest_flags = []
    if by_week:
        latest_week = max(by_week)
        for run in by_week[latest_week]:
            mentions = run_mentions(run, entities)
            latest_flags.append(brand_is_cited(mentions, run.citations, brand))
    current_rate = citation_rate(latest_flags)
    previous_rate = trend[-2].citation_rate if len(trend) >= 2 else None
    shares, counts = _sov_for(by_week[max(by_week)], entities) if by_week else ({}, {})
    previous_shares = {}
    if len(trend) >= 2 and by_week:
        weeks = sorted(by_week)
        previous_shares, _previous_counts = _sov_for(by_week[weeks[-2]], entities)
    current_sov = shares.get(brand.name) if shares else None
    previous_sov = previous_shares.get(brand.name) if previous_shares else None

    ordered_audits = sorted(workspace.audits, key=lambda item: item.created_at)
    geo = ordered_audits[-1].draft.score if ordered_audits else None
    geo_delta = None
    if len(ordered_audits) >= 2:
        geo_delta = ordered_audits[-1].draft.score - ordered_audits[-2].draft.score

    top = sorted(domain_gaps(workspace), key=lambda item: item.citations, reverse=True)[:6]
    return OverviewOut(
        workspace_name=workspace.name,
        brand_name=workspace.brand_name,
        domain=workspace.domain,
        sector=workspace.sector,
        llm_mode=llm_mode(workspace),  # type: ignore[arg-type]
        methodology=METHODOLOGY,
        kpis=Kpis(
            geo_score=geo,
            geo_score_delta=geo_delta,
            citation_rate=current_rate,
            citation_rate_delta=None if current_rate is None or previous_rate is None else current_rate - previous_rate,
            share_of_voice=current_sov,
            share_of_voice_delta=None if current_sov is None or previous_sov is None else current_sov - previous_sov,
            queries_tracked=sum(1 for query in workspace.queries if query.active),
            runs_completed=len(completed),
        ),
        trend=trend,
        share_of_voice=[
            SovSlice(
                name=entity.name,
                kind=entity.kind,  # type: ignore[arg-type]
                share=shares.get(entity.name, 0.0) if shares else 0.0,
                mentions=counts.get(entity.name, 0) if counts else 0,
            )
            for entity in entities
        ],
        top_domains=[
            DomainStat(domain=item.domain, citations=item.citations, runs_without_brand=item.runs_without_brand)
            for item in top
        ],
    )


def build_tracking(workspace: Workspace) -> TrackingOut:
    entities = entities_of(workspace)
    latest: dict[tuple[str, str], StoredRun] = {}
    for run in workspace.runs:
        key = (run.query_id, run.provider)
        current = latest.get(key)
        if current is None or run.created_at >= current.created_at:
            latest[key] = run
    queries: list[QueryTrackingOut] = []
    for query in workspace.queries:
        runs = {}
        for provider in workspace.providers:
            found = latest.get((query.id, provider))
            runs[provider] = project_run(found, entities) if found else None
        queries.append(QueryTrackingOut(id=query.id, prompt=query.prompt, active=query.active, runs=runs))
    return TrackingOut(
        queries=queries,
        providers=list(workspace.providers),  # type: ignore[arg-type]
        llm_mode=llm_mode(workspace),  # type: ignore[arg-type]
    )


def discovered_competitors(workspace: Workspace) -> list[DiscoveredCompetitor]:
    """Marques les plus nommées par les moteurs sur les questions du client."""
    return [
        DiscoveredCompetitor(name=item.name, domain=item.domain, mentions=item.mentions, providers=list(item.providers))
        for item in market_rivals(workspace)[:6]
    ]


def _audit_out(workspace: Workspace, audit: StoredAudit) -> AuditOut:
    discovered = discovered_competitors(workspace)
    recommendations = build_recommendations(
        audit.draft,
        domain_gaps(workspace),
        [item.name for item in discovered],
    )
    return AuditOut(
        id=audit.id,
        url=audit.draft.url,
        score=audit.draft.score,
        heading_score=audit.draft.heading_score,
        schema_score=audit.draft.schema_score,
        factual_score=audit.draft.factual_score,
        crawler_score=audit.draft.crawler_score,
        pages_crawled=audit.draft.pages_crawled,
        checks=[
            CheckOut(id=item.id, label=item.label, status=item.status, score=item.score, detail=item.detail)  # type: ignore[arg-type]
            for item in audit.draft.checks
        ],
        recommendations=[
            RecommendationOut(
                id=item.id,
                priority=item.priority,  # type: ignore[arg-type]
                category=item.category,  # type: ignore[arg-type]
                title=item.title,
                detail=item.detail,
                effort=item.effort,  # type: ignore[arg-type]
                steps=list(item.steps),
            )
            for item in recommendations
        ],
        created_at=audit.created_at,
    )


def build_audit(workspace: Workspace) -> AuditResponse:
    ordered = sorted(workspace.audits, key=lambda item: item.created_at)
    history_map: dict[datetime, int] = {}
    for audit in ordered:
        history_map[week_start(audit.created_at)] = audit.draft.score
    history = [
        AuditHistoryPoint(week=week.date().isoformat(), score=score) for week, score in sorted(history_map.items())
    ]
    latest = _audit_out(workspace, ordered[-1]) if ordered else None
    return AuditResponse(audit=latest, history=history, discovered_competitors=discovered_competitors(workspace))
