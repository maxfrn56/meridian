from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, timedelta, timezone

from security import hash_password
from services.auditor import audit_documents
from services.simulator import simulate_answer
from services.tracker import citations_from_sources, entities_from_workspace
from store import Competitor, Query, StoredAudit, StoredRun, User, Workspace, store

DEMO_EMAIL = "demo@geo.dev"
DEMO_PASSWORD = "meridian"

QUERIES = (
    "Quel est le meilleur outil de product analytics pour une scale-up SaaS en 2026 ?",
    "Northwind ou Lumenboard pour l'analyse produit ?",
    "Quelles alternatives à Amplitude pour une équipe produit européenne ?",
    "Comment mesurer l'activation et la rétention dans un SaaS B2B ?",
    "Quels outils de product analytics sont conformes au RGPD ?",
    "Comparatif des plateformes d'analytics produit : prix, intégrations, entrepôt.",
    "Quel outil pour relier les événements produit à un data warehouse ?",
    "Comment instrumenter une application Next.js sans perdre les événements ?",
    "Stackmetric ou ClarityForge pour une équipe growth ?",
    "Comment les équipes produit choisissent-elles leur outil d'analytics ?",
    "Pulsegrid est-il adapté au suivi des funnels B2B ?",
    "Où trouver des benchmarks de rétention SaaS B2B fiables ?",
)

COMPETITORS = (
    ("Lumenboard", "lumenboard.com"),
    ("Stackmetric", "stackmetric.io"),
    ("ClarityForge", "clarityforge.com"),
    ("Pulsegrid", "pulsegrid.dev"),
)


def _rng(*parts: object) -> random.Random:
    raw = "|".join(str(part) for part in parts)
    seed = int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def build_sample_site(level: int) -> tuple[str, str, str | None]:
    questions = [
        "Comment mesurer l'activation dans un SaaS B2B ?",
        "Pourquoi les équipes produit changent-elles d'outil d'analytics ?",
        "Quel entrepôt de données connecter en premier ?",
        "Comment instrumenter une application Next.js ?",
    ]
    plain = ["Plateforme d'analytics produit", "Tarifs et déploiement"]
    question_count = min(len(questions), max(0, level - 1))
    blocks = [f"<h2>{item}</h2><p>Réponse autonome, en moins de quatre-vingts mots.</p>" for item in questions[:question_count]]
    blocks.extend(f"<h2>{item}</h2><p>Présentation générale de l'offre.</p>" for item in plain)
    stats = "".join(
        f"<p>{40 + index * 7} % des équipes activent le suivi en moins de 14 j.</p>"
        for index in range(min(level, 4))
    )
    items = "".join(f"<li>Signal {index + 1} : événement instrumenté</li>" for index in range(min(level, 6)))
    list_html = f"<ul>{items}</ul>" if items else ""
    table = ""
    if level >= 4:
        table = (
            "<table><thead><tr><th>Plan</th><th>Événements</th></tr></thead>"
            "<tbody><tr><td>Growth</td><td>50 M</td></tr></tbody></table>"
        )
    schemas: list[str] = []
    if level >= 3:
        schemas.append(
            '{"@context":"https://schema.org","@type":"Organization","name":"Northwind","url":"https://northwind.io"}'
        )
    if level >= 5:
        schemas.append('{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}')
    if level >= 6:
        schemas.append(
            '{"@context":"https://schema.org","@type":"Article","headline":"Mesurer l activation produit"}'
        )
    scripts = "".join(f'<script type="application/ld+json">{block}</script>' for block in schemas)
    html = (
        "<!doctype html><html><head><title>Northwind</title>"
        f"{scripts}</head><body><h1>Northwind</h1>{''.join(blocks)}{stats}{list_html}{table}</body></html>"
    )
    if level < 4:
        robots = (
            "User-agent: *\nDisallow:\n\n"
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: PerplexityBot\nDisallow: /\n\n"
            "User-agent: ClaudeBot\nDisallow: /\n"
        )
    else:
        robots = (
            "User-agent: *\nAllow: /\n\n"
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: PerplexityBot\nAllow: /\n\n"
            "User-agent: ClaudeBot\nAllow: /\n"
        )
    llms = None
    if level >= 5:
        llms = "# Northwind\n\n> Analytics produit pour les scale-ups.\n\n## Pages\n- https://northwind.io/faq\n"
    return html, robots, llms


def seed_demo(target: store.__class__ | None = None) -> None:
    destination = target or store
    if destination.user_by_email(DEMO_EMAIL):
        return
    user = User(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, DEMO_EMAIL).hex,
        name="Camille Martin",
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
    )
    competitors = [
        Competitor(id=uuid.uuid5(uuid.NAMESPACE_URL, domain).hex, name=name, domain=domain)
        for name, domain in COMPETITORS
    ]
    queries = [
        Query(id=uuid.uuid5(uuid.NAMESPACE_URL, prompt).hex, prompt=prompt, active=True) for prompt in QUERIES
    ]
    workspace = Workspace(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, "northwind").hex,
        user_id=user.id,
        name="Northwind",
        brand_name="Northwind",
        domain="northwind.io",
        sector="Product analytics",
        competitors=competitors,
        queries=queries,
        plan_id="croissance",
        period_month=datetime.now(timezone.utc).strftime("%Y-%m"),
        questions_used=0,
    )
    destination.add_user(user, workspace)
    entities = entities_from_workspace(
        workspace.brand_name,
        workspace.domain,
        [(item.name, item.domain) for item in competitors],
    )
    now = datetime.now(timezone.utc)
    runs: list[StoredRun] = []
    for week in range(8):
        created_base = now - timedelta(weeks=7 - week, days=1)
        for query in queries:
            for provider in ("openai", "perplexity", "gemini"):
                rng = _rng(query.prompt, provider, week)
                text, sources = simulate_answer(query.prompt, provider, entities, rng, week_index=week)
                runs.append(
                    StoredRun(
                        id=uuid.uuid4().hex,
                        query_id=query.id,
                        query_prompt=query.prompt,
                        provider=provider,
                        model={"openai": "gpt-4o", "perplexity": "sonar", "gemini": "gemini-2.5-flash"}[provider],
                        status="completed",
                        source="mock",
                        response_text=text,
                        citations=citations_from_sources(sources),
                        error=None,
                        created_at=created_base.replace(hour=9, minute=rng.randint(0, 50), second=0, microsecond=0),
                    )
                )
        html, robots, llms = build_sample_site(week)
        destination.add_audit(
            user.id,
            StoredAudit(
                id=uuid.uuid4().hex,
                draft=audit_documents([( "https://northwind.io/", html)], robots, llms, "https://northwind.io/"),
                created_at=created_base.replace(hour=7, minute=0, second=0, microsecond=0),
            ),
        )
    destination.add_runs(user.id, runs)
