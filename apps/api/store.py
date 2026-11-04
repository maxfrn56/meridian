from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from services.analyzer import Citation, normalize_domain
from services.auditor import AuditDraft


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: str


@dataclass
class Competitor:
    id: str
    name: str
    domain: str


@dataclass
class Query:
    id: str
    prompt: str
    active: bool


@dataclass
class StoredRun:
    id: str
    query_id: str
    query_prompt: str
    provider: str
    model: str
    status: str
    source: str
    response_text: str
    citations: list[Citation]
    error: str | None
    created_at: datetime


@dataclass
class StoredAudit:
    id: str
    draft: AuditDraft
    created_at: datetime


@dataclass
class Workspace:
    id: str
    user_id: str
    name: str
    brand_name: str
    domain: str
    sector: str
    competitors: list[Competitor] = field(default_factory=list)
    queries: list[Query] = field(default_factory=list)
    runs: list[StoredRun] = field(default_factory=list)
    audits: list[StoredAudit] = field(default_factory=list)
    plan_id: str | None = None
    period_month: str = ""
    questions_used: int = 0


class Store:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.users: dict[str, User] = {}
        self.by_email: dict[str, str] = {}
        self.workspaces: dict[str, Workspace] = {}

    def reset(self) -> None:
        with self._lock:
            self.users.clear()
            self.by_email.clear()
            self.workspaces.clear()

    def user_by_id(self, user_id: str) -> User | None:
        with self._lock:
            return self.users.get(user_id)

    def user_by_email(self, email: str) -> User | None:
        with self._lock:
            user_id = self.by_email.get(email.lower())
            return self.users.get(user_id) if user_id else None

    def workspace_for(self, user_id: str) -> Workspace | None:
        with self._lock:
            return self.workspaces.get(user_id)

    def add_user(self, user: User, workspace: Workspace) -> None:
        with self._lock:
            if user.email.lower() in self.by_email:
                raise ValueError("Un compte existe déjà avec cet e-mail.")
            self.users[user.id] = user
            self.by_email[user.email.lower()] = user.id
            self.workspaces[user.id] = workspace

    def update_settings(
        self,
        user_id: str,
        workspace_name: str,
        brand_name: str,
        domain: str,
        sector: str,
        competitors: list[tuple[str, str]],
        queries: list[tuple[str, bool]],
    ) -> Workspace:
        with self._lock:
            workspace = self.workspaces[user_id]
            cleaned_domain = normalize_domain(domain)
            if not cleaned_domain:
                raise ValueError("Le domaine de la marque est requis.")
            if len(competitors) > 5:
                raise ValueError("Cinq concurrents maximum.")
            if len(queries) > 60:
                raise ValueError("Soixante requêtes maximum.")
            seen_domains: set[str] = set()
            next_competitors: list[Competitor] = []
            current = {item.domain: item for item in workspace.competitors}
            for name, raw_domain in competitors:
                competitor_domain = normalize_domain(raw_domain)
                if competitor_domain in seen_domains:
                    raise ValueError(f"Le domaine {competitor_domain} est en double.")
                if competitor_domain == cleaned_domain:
                    raise ValueError("Un concurrent ne peut pas partager le domaine de la marque.")
                seen_domains.add(competitor_domain)
                previous = current.get(competitor_domain)
                next_competitors.append(
                    Competitor(
                        id=previous.id if previous else uuid.uuid4().hex,
                        name=name.strip(),
                        domain=competitor_domain,
                    )
                )
            seen_prompts: set[str] = set()
            next_queries: list[Query] = []
            current_queries = {item.prompt: item for item in workspace.queries}
            for prompt, active in queries:
                cleaned = " ".join(prompt.split())
                if cleaned in seen_prompts:
                    raise ValueError("Deux requêtes sont identiques.")
                seen_prompts.add(cleaned)
                previous = current_queries.get(cleaned)
                next_queries.append(
                    Query(
                        id=previous.id if previous else uuid.uuid4().hex,
                        prompt=cleaned,
                        active=active,
                    )
                )
            workspace.name = workspace_name.strip()
            workspace.brand_name = brand_name.strip()
            workspace.domain = cleaned_domain
            workspace.sector = sector.strip()
            workspace.competitors = next_competitors
            workspace.queries = next_queries
            return workspace

    def _roll_period(self, workspace: Workspace) -> None:
        month = date.today().strftime("%Y-%m")
        if workspace.period_month != month:
            workspace.period_month = month
            workspace.questions_used = 0

    def current_workspace(self, user_id: str) -> Workspace:
        with self._lock:
            workspace = self.workspaces[user_id]
            self._roll_period(workspace)
            return workspace

    def activate_plan(self, user_id: str, plan_id: str) -> Workspace:
        with self._lock:
            workspace = self.workspaces[user_id]
            self._roll_period(workspace)
            workspace.plan_id = plan_id
            return workspace

    def consume_questions(self, user_id: str, count: int) -> None:
        with self._lock:
            workspace = self.workspaces[user_id]
            self._roll_period(workspace)
            workspace.questions_used += count

    def add_runs(self, user_id: str, runs: list[StoredRun]) -> None:
        with self._lock:
            self.workspaces[user_id].runs.extend(runs)

    def add_audit(self, user_id: str, audit: StoredAudit) -> None:
        with self._lock:
            self.workspaces[user_id].audits.append(audit)


store = Store()
