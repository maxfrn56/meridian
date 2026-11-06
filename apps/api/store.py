"""Accès aux données.

Les services (metrics, comparison, recommender…) travaillent sur des dataclasses simples.
Ce module les lit et les écrit dans la base via SQLAlchemy : les services ne voient pas SQL.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload, sessionmaker

from config import ENGINES
from db import SessionLocal
from models.tables import (
    AuditRow,
    Base,
    CitationRow,
    MentionRow,
    QueryRow,
    TrackingRunRow,
    UserRow,
    WorkspaceRow,
)
from services.analyzer import AnalyzedMention, Citation, normalize_domain
from services.auditor import AuditDraft, Check


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: str
    role: str = "client"
    email_verified: bool = True
    session_version: int = 0
    verify_token_hash: str = ""
    verify_expires_at: datetime | None = None
    reset_token_hash: str = ""
    reset_expires_at: datetime | None = None
    last_verify_mail_at: datetime | None = None
    last_reset_mail_at: datetime | None = None


@dataclass
class Query:
    id: str
    prompt: str
    active: bool
    tag: str = ""


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
    # None : pas d'analyse LLM, les métriques retombent sur l'analyse par mots-clés.
    analysis: list[AnalyzedMention] | None = None
    analysis_version: str = ""


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
    queries: list[Query] = field(default_factory=list)
    runs: list[StoredRun] = field(default_factory=list)
    audits: list[StoredAudit] = field(default_factory=list)
    plan_id: str | None = None
    period_month: str = ""
    questions_used: int = 0
    providers: tuple[str, ...] = ("openai", "perplexity", "gemini")
    trial_ends_at: datetime | None = None


_KNOWN_ENGINES = set(ENGINES)
_DEFAULT_ENGINES = ("openai", "perplexity", "gemini")


def _providers(value: str | None) -> tuple[str, ...]:
    items = [part.strip() for part in (value or "").split(",") if part.strip() in _KNOWN_ENGINES]
    if len(items) != 3 or len(set(items)) != 3:
        return _DEFAULT_ENGINES
    return tuple(items)


def _aware(value: datetime) -> datetime:
    """SQLite rend des dates sans fuseau : on les remet en UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _current_day() -> str:
    """Jour UTC du compteur : le forfait autorise un nombre de questions chaque jour."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _optional_time(value: datetime | None) -> datetime | None:
    return _aware(value) if value else None


def _user(row: UserRow) -> User:
    return User(
        id=row.id,
        name=row.name,
        email=row.email,
        password_hash=row.password_hash,
        role=row.role,
        email_verified=row.email_verified,
        session_version=row.session_version,
        verify_token_hash=row.verify_token_hash,
        verify_expires_at=_optional_time(row.verify_expires_at),
        reset_token_hash=row.reset_token_hash,
        reset_expires_at=_optional_time(row.reset_expires_at),
        last_verify_mail_at=_optional_time(row.last_verify_mail_at),
        last_reset_mail_at=_optional_time(row.last_reset_mail_at),
    )


def _run(row: TrackingRunRow) -> StoredRun:
    return StoredRun(
        id=row.id,
        query_id=row.query_id,
        query_prompt=row.query_prompt,
        provider=row.provider,
        model=row.model,
        status=row.status,
        source=row.source,
        response_text=row.response_text,
        citations=[
            Citation(url=item.url, domain=item.domain, title=item.title, position=item.position)
            for item in row.citations
        ],
        error=row.error,
        created_at=_aware(row.created_at),
        analysis=(
            [
                AnalyzedMention(
                    name=item.name,
                    domain=item.domain,
                    position=item.position,
                    stance=item.stance,
                    sentiment=item.sentiment,
                    excerpt=item.excerpt,
                )
                for item in row.mentions
            ]
            if row.analysis_method == "llm"
            else None
        ),
        analysis_version=row.analysis_version,
    )


def _mention_rows(analysis: list[AnalyzedMention]) -> list[MentionRow]:
    return [
        MentionRow(
            name=item.name,
            domain=item.domain,
            position=item.position,
            stance=item.stance,
            sentiment=item.sentiment,
            excerpt=item.excerpt,
        )
        for item in analysis
    ]


def _draft_to_json(draft: AuditDraft) -> dict:
    return asdict(draft)


def _draft_from_json(data: dict) -> AuditDraft:
    values = dict(data)
    values["checks"] = [Check(**item) for item in values.get("checks", [])]
    return AuditDraft(**values)


def _audit(row: AuditRow) -> StoredAudit:
    return StoredAudit(id=row.id, draft=_draft_from_json(row.data), created_at=_aware(row.created_at))


class Store:
    def __init__(self, sessions: sessionmaker[Session] = SessionLocal) -> None:
        self._sessions = sessions

    def _session(self) -> Session:
        return self._sessions()

    # Utilisé par les tests.
    def reset(self) -> None:
        with self._session() as session, session.begin():
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(delete(table))

    # Comptes

    def user_by_id(self, user_id: str) -> User | None:
        with self._session() as session:
            row = session.get(UserRow, user_id)
            return _user(row) if row else None

    def user_by_email(self, email: str) -> User | None:
        with self._session() as session:
            row = session.scalar(select(UserRow).where(UserRow.email == email.lower()))
            return _user(row) if row else None

    def add_user(self, user: User, workspace: Workspace) -> None:
        with self._session() as session, session.begin():
            exists = session.scalar(select(UserRow.id).where(UserRow.email == user.email.lower()))
            if exists:
                raise ValueError("Un compte existe déjà avec cet e-mail.")
            session.add(
                UserRow(
                    id=user.id,
                    name=user.name,
                    email=user.email.lower(),
                    password_hash=user.password_hash,
                    role=user.role,
                    email_verified=user.email_verified,
                    session_version=user.session_version,
                )
            )
            session.add(
                WorkspaceRow(
                    id=workspace.id,
                    user_id=user.id,
                    name=workspace.name,
                    brand_name=workspace.brand_name,
                    domain=workspace.domain,
                    sector=workspace.sector,
                    plan_id=workspace.plan_id,
                    period_month=workspace.period_month,
                    questions_used=workspace.questions_used,
                    providers=",".join(workspace.providers),
                    trial_ends_at=workspace.trial_ends_at,
                    queries=[
                        QueryRow(id=item.id, prompt=item.prompt, active=item.active, position=index)
                        for index, item in enumerate(workspace.queries)
                    ],
                )
            )

    def add_admin(self, user: User) -> None:
        """Compte interne, sans espace client."""
        with self._session() as session, session.begin():
            exists = session.scalar(select(UserRow.id).where(UserRow.email == user.email.lower()))
            if exists:
                raise ValueError("Un compte existe déjà avec cet e-mail.")
            session.add(
                UserRow(
                    id=user.id,
                    name=user.name,
                    email=user.email.lower(),
                    password_hash=user.password_hash,
                    role="admin",
                    email_verified=True,
                    session_version=user.session_version,
                )
            )

    def set_role(self, user_id: str, role: str) -> None:
        with self._session() as session, session.begin():
            session.execute(update(UserRow).where(UserRow.id == user_id).values(role=role))

    def adopt_admin(self, user_id: str, password_hash: str | None) -> None:
        """Passe le compte en administrateur, confirmé, avec le mot de passe indiqué s'il change."""
        with self._session() as session, session.begin():
            row = session.get(UserRow, user_id)
            if row is None:
                return
            row.role = "admin"
            row.email_verified = True
            if password_hash:
                row.password_hash = password_hash
                row.session_version += 1

    def delete_user(self, user_id: str) -> None:
        with self._session() as session, session.begin():
            session.execute(delete(UserRow).where(UserRow.id == user_id))

    def stage_token(self, user_id: str, purpose: str, token_hash: str, expires_at: datetime, *, force: bool) -> bool:
        with self._session() as session, session.begin():
            row = session.get(UserRow, user_id)
            if row is None:
                return False
            now = datetime.now(timezone.utc)
            last_mail = row.last_verify_mail_at if purpose == "verify" else row.last_reset_mail_at
            if not force and last_mail and (now - _aware(last_mail)).total_seconds() < 60:
                return False
            if purpose == "verify":
                row.verify_token_hash = token_hash
                row.verify_expires_at = expires_at
            else:
                row.reset_token_hash = token_hash
                row.reset_expires_at = expires_at
            return True

    def mark_mail_sent(self, user_id: str, purpose: str) -> None:
        with self._session() as session, session.begin():
            row = session.get(UserRow, user_id)
            if row is None:
                return
            stamp = datetime.now(timezone.utc)
            if purpose == "verify":
                row.last_verify_mail_at = stamp
            else:
                row.last_reset_mail_at = stamp

    def confirm_email(self, token_hash: str) -> bool:
        with self._session() as session, session.begin():
            row = session.scalar(select(UserRow).where(UserRow.verify_token_hash == token_hash))
            if row is None or not row.verify_expires_at or _aware(row.verify_expires_at) < datetime.now(timezone.utc):
                return False
            row.email_verified = True
            row.verify_token_hash = ""
            row.verify_expires_at = None
            return True

    def reset_password(self, token_hash: str, password_hash: str) -> bool:
        with self._session() as session, session.begin():
            row = session.scalar(select(UserRow).where(UserRow.reset_token_hash == token_hash))
            if row is None or not row.reset_expires_at or _aware(row.reset_expires_at) < datetime.now(timezone.utc):
                return False
            row.password_hash = password_hash
            row.email_verified = True
            row.session_version += 1
            row.reset_token_hash = ""
            row.reset_expires_at = None
            return True

    # Espace client

    def _workspace_row(self, session: Session, user_id: str) -> WorkspaceRow | None:
        return session.scalar(
            select(WorkspaceRow)
            .where(WorkspaceRow.user_id == user_id)
            .options(selectinload(WorkspaceRow.queries))
        )

    def _load(self, session: Session, row: WorkspaceRow) -> Workspace:
        runs = session.scalars(
            select(TrackingRunRow)
            .where(TrackingRunRow.workspace_id == row.id)
            .order_by(TrackingRunRow.created_at)
            .options(selectinload(TrackingRunRow.citations), selectinload(TrackingRunRow.mentions))
        ).all()
        audits = session.scalars(
            select(AuditRow).where(AuditRow.workspace_id == row.id).order_by(AuditRow.created_at)
        ).all()
        return Workspace(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            brand_name=row.brand_name,
            domain=row.domain,
            sector=row.sector,
            queries=[
                Query(id=item.id, prompt=item.prompt, active=item.active, tag=item.tag or "")
                for item in sorted(row.queries, key=lambda item: (item.position, item.prompt))
            ],
            runs=[_run(item) for item in runs],
            audits=[_audit(item) for item in audits],
            plan_id=row.plan_id,
            period_month=row.period_month,
            questions_used=row.questions_used,
            providers=_providers(row.providers),
            trial_ends_at=_aware(row.trial_ends_at) if row.trial_ends_at else None,
        )

    def _roll_period(self, row: WorkspaceRow) -> None:
        day = _current_day()
        stored = row.period_month or ""
        if stored == day:
            return
        # Ancien tampon AAAA-MM, trop court pour le jour : on l'allonge sans
        # effacer le compteur à chaque lecture, sinon il reste affiché à zéro.
        if len(stored) == 7 and day.startswith(stored):
            row.period_month = day
            return
        row.period_month = day
        row.questions_used = 0

    def workspace_user_ids(self) -> list[str]:
        with self._session() as session:
            return list(session.scalars(select(WorkspaceRow.user_id)).all())

    def workspace_for(self, user_id: str) -> Workspace | None:
        with self._session() as session:
            row = self._workspace_row(session, user_id)
            return self._load(session, row) if row else None

    def current_workspace(self, user_id: str) -> Workspace:
        """Espace à jour, compteur du jour remis à zéro si le jour a changé."""
        with self._session() as session, session.begin():
            row = self._workspace_row(session, user_id)
            if row is None:
                raise KeyError(user_id)
            self._roll_period(row)
            session.flush()
            return self._load(session, row)

    def update_settings(
        self,
        user_id: str,
        workspace_name: str,
        brand_name: str,
        domain: str,
        sector: str,
        queries: list[tuple[str, bool, str]],
        providers: list[str] | None = None,
    ) -> Workspace:
        cleaned_domain = normalize_domain(domain)
        if not cleaned_domain:
            raise ValueError("Le domaine de la marque est requis.")
        if len(queries) > 200:
            raise ValueError("Deux cents requêtes maximum.")

        seen_prompts: set[str] = set()
        wanted_queries: list[tuple[str, bool, str]] = []
        for prompt, active, tag in queries:
            cleaned = " ".join(prompt.split())
            label = " ".join(tag.split())[:40]
            if cleaned in seen_prompts:
                raise ValueError("Deux requêtes sont identiques.")
            seen_prompts.add(cleaned)
            wanted_queries.append((cleaned, active, label))

        with self._session() as session, session.begin():
            row = self._workspace_row(session, user_id)
            if row is None:
                raise KeyError(user_id)
            # On garde les identifiants existants : l'historique des runs y reste rattaché.
            current_queries = {item.prompt: item for item in row.queries}
            next_queries: list[QueryRow] = []
            for index, (prompt, active, tag) in enumerate(wanted_queries):
                item = current_queries.pop(prompt, None)
                if item is None:
                    item = QueryRow(id=uuid.uuid4().hex, prompt=prompt)
                item.active = active
                item.tag = tag
                item.position = index
                next_queries.append(item)

            row.name = workspace_name.strip()
            row.brand_name = brand_name.strip()
            row.domain = cleaned_domain
            row.sector = sector.strip()
            if providers:
                row.providers = ",".join(providers)
            row.queries = next_queries
            session.flush()
            return self._load(session, row)

    # Forfait

    def activate_plan(self, user_id: str, plan_id: str) -> Workspace:
        with self._session() as session, session.begin():
            row = self._workspace_row(session, user_id)
            if row is None:
                raise KeyError(user_id)
            self._roll_period(row)
            row.plan_id = plan_id
            session.flush()
            return self._load(session, row)

    def stripe_customer_id(self, workspace_id: str) -> str | None:
        with self._session() as session:
            row = session.get(WorkspaceRow, workspace_id)
            if row is None:
                return None
            return row.stripe_customer_id or None

    def apply_paid_plan(
        self,
        workspace_id: str,
        plan_id: str,
        customer_id: str,
        subscription_id: str,
    ) -> str | None:
        """Active le forfait payé. Retourne l'abonnement précédent à résilier, ou None si l'espace n'existe pas."""
        with self._session() as session, session.begin():
            row = session.get(WorkspaceRow, workspace_id)
            if row is None:
                return None
            previous = row.stripe_subscription_id or ""
            self._roll_period(row)
            row.plan_id = plan_id
            if customer_id:
                row.stripe_customer_id = customer_id
            if subscription_id:
                row.stripe_subscription_id = subscription_id
            session.flush()
            if previous and previous != subscription_id:
                return previous
            return ""

    def clear_paid_plan(self, workspace_id: str) -> None:
        with self._session() as session, session.begin():
            row = session.get(WorkspaceRow, workspace_id)
            if row is None:
                return
            row.plan_id = None
            row.stripe_subscription_id = None

    def consume_questions(self, user_id: str, count: int) -> None:
        with self._session() as session, session.begin():
            row = self._workspace_row(session, user_id)
            if row is None:
                raise KeyError(user_id)
            self._roll_period(row)
            row.questions_used += count

    # Résultats

    def _workspace_id(self, session: Session, user_id: str) -> str:
        workspace_id = session.scalar(select(WorkspaceRow.id).where(WorkspaceRow.user_id == user_id))
        if workspace_id is None:
            raise KeyError(user_id)
        return workspace_id

    def add_runs(self, user_id: str, runs: list[StoredRun]) -> None:
        with self._session() as session, session.begin():
            workspace_id = self._workspace_id(session, user_id)
            session.add_all(
                TrackingRunRow(
                    id=run.id,
                    workspace_id=workspace_id,
                    query_id=run.query_id,
                    query_prompt=run.query_prompt,
                    provider=run.provider,
                    model=run.model,
                    status=run.status,
                    source=run.source,
                    response_text=run.response_text,
                    error=run.error,
                    created_at=run.created_at,
                    citations=[
                        CitationRow(url=item.url, domain=item.domain, title=item.title, position=item.position)
                        for item in run.citations
                    ],
                    analysis_method="llm" if run.analysis is not None else "",
                    analysis_version=run.analysis_version if run.analysis is not None else "",
                    mentions=_mention_rows(run.analysis) if run.analysis is not None else [],
                )
                for run in runs
            )

    def save_analysis(self, run_id: str, analysis: list[AnalyzedMention], version: str) -> bool:
        """Remplace l'analyse LLM d'une réponse déjà enregistrée (nouvelle version du prompt)."""
        with self._session() as session, session.begin():
            row = session.get(TrackingRunRow, run_id, options=[selectinload(TrackingRunRow.mentions)])
            if row is None:
                return False
            row.mentions = _mention_rows(analysis)
            row.analysis_method = "llm"
            row.analysis_version = version
            return True

    def add_audit(self, user_id: str, audit: StoredAudit) -> None:
        with self._session() as session, session.begin():
            workspace_id = self._workspace_id(session, user_id)
            session.add(
                AuditRow(
                    id=audit.id,
                    workspace_id=workspace_id,
                    url=audit.draft.url,
                    score=audit.draft.score,
                    data=_draft_to_json(audit.draft),
                    created_at=audit.created_at,
                )
            )


store = Store()
