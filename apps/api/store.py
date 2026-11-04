"""Accès aux données.

Les services (metrics, comparison, recommender…) travaillent sur des dataclasses simples.
Ce module les lit et les écrit dans la base via SQLAlchemy : les services ne voient pas SQL.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload, sessionmaker

from db import SessionLocal
from models.tables import (
    AuditRow,
    Base,
    CitationRow,
    CompetitorRow,
    QueryRow,
    TrackingRunRow,
    UserRow,
    WorkspaceRow,
)
from services.analyzer import Citation, normalize_domain
from services.auditor import AuditDraft, Check


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: str
    email_verified: bool = True
    session_version: int = 0
    verify_token_hash: str = ""
    verify_expires_at: datetime | None = None
    reset_token_hash: str = ""
    reset_expires_at: datetime | None = None
    last_verify_mail_at: datetime | None = None
    last_reset_mail_at: datetime | None = None


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


def _aware(value: datetime) -> datetime:
    """SQLite rend des dates sans fuseau : on les remet en UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _optional_time(value: datetime | None) -> datetime | None:
    return _aware(value) if value else None


def _user(row: UserRow) -> User:
    return User(
        id=row.id,
        name=row.name,
        email=row.email,
        password_hash=row.password_hash,
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
    )


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
                    competitors=[
                        CompetitorRow(id=item.id, name=item.name, domain=item.domain, position=index)
                        for index, item in enumerate(workspace.competitors)
                    ],
                    queries=[
                        QueryRow(id=item.id, prompt=item.prompt, active=item.active, position=index)
                        for index, item in enumerate(workspace.queries)
                    ],
                )
            )

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
            .options(selectinload(WorkspaceRow.competitors), selectinload(WorkspaceRow.queries))
        )

    def _load(self, session: Session, row: WorkspaceRow) -> Workspace:
        runs = session.scalars(
            select(TrackingRunRow)
            .where(TrackingRunRow.workspace_id == row.id)
            .order_by(TrackingRunRow.created_at)
            .options(selectinload(TrackingRunRow.citations))
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
            competitors=[Competitor(id=item.id, name=item.name, domain=item.domain) for item in row.competitors],
            queries=[Query(id=item.id, prompt=item.prompt, active=item.active) for item in row.queries],
            runs=[_run(item) for item in runs],
            audits=[_audit(item) for item in audits],
            plan_id=row.plan_id,
            period_month=row.period_month,
            questions_used=row.questions_used,
        )

    def _roll_period(self, row: WorkspaceRow) -> None:
        month = _current_month()
        if row.period_month != month:
            row.period_month = month
            row.questions_used = 0

    def workspace_for(self, user_id: str) -> Workspace | None:
        with self._session() as session:
            row = self._workspace_row(session, user_id)
            return self._load(session, row) if row else None

    def current_workspace(self, user_id: str) -> Workspace:
        """Espace à jour, compteur du mois remis à zéro si le mois a changé."""
        with self._session() as session, session.begin():
            row = self._workspace_row(session, user_id)
            if row is None:
                raise KeyError(user_id)
            self._roll_period(row)
            session.flush()
            return self._load(session, row)

    def delete_user(self, user_id: str) -> None:
        with self._lock:
            user = self.users.pop(user_id, None)
            if user is None:
                return
            self.by_email.pop(user.email.lower(), None)
            self.workspaces.pop(user_id, None)
            self._drop(self.verify_index, user_id)
            self._drop(self.reset_index, user_id)

    def stage_token(self, user_id: str, purpose: str, token_hash: str, expires_at: datetime, *, force: bool) -> bool:
        with self._lock:
            user = self.users[user_id]
            now = datetime.now(timezone.utc)
            last_mail = user.last_verify_mail_at if purpose == "verify" else user.last_reset_mail_at
            if not force and last_mail and (now - last_mail).total_seconds() < 60:
                return False
            index = self.verify_index if purpose == "verify" else self.reset_index
            self._drop(index, user_id)
            if purpose == "verify":
                user.verify_token_hash = token_hash
                user.verify_expires_at = expires_at
            else:
                user.reset_token_hash = token_hash
                user.reset_expires_at = expires_at
            index[token_hash] = user_id
            return True

    def mark_mail_sent(self, user_id: str, purpose: str) -> None:
        with self._lock:
            user = self.users.get(user_id)
            if user is None:
                return
            stamp = datetime.now(timezone.utc)
            if purpose == "verify":
                user.last_verify_mail_at = stamp
            else:
                user.last_reset_mail_at = stamp

    def confirm_email(self, token_hash: str) -> bool:
        with self._lock:
            user = self._user_for_token(self.verify_index, token_hash, "verify")
            if user is None:
                return False
            user.email_verified = True
            user.verify_token_hash = ""
            user.verify_expires_at = None
            self.verify_index.pop(token_hash, None)
            return True

    def reset_password(self, token_hash: str, password_hash: str) -> bool:
        with self._lock:
            user = self._user_for_token(self.reset_index, token_hash, "reset")
            if user is None:
                return False
            user.password_hash = password_hash
            user.email_verified = True
            user.session_version += 1
            user.reset_token_hash = ""
            user.reset_expires_at = None
            self.reset_index.pop(token_hash, None)
            return True

    def _user_for_token(self, index: dict[str, str], token_hash: str, purpose: str) -> User | None:
        user_id = index.get(token_hash)
        user = self.users.get(user_id) if user_id else None
        if user is None:
            return None
        stored = user.verify_token_hash if purpose == "verify" else user.reset_token_hash
        expires = user.verify_expires_at if purpose == "verify" else user.reset_expires_at
        if stored != token_hash or expires is None or expires < datetime.now(timezone.utc):
            return None
        return user

    def _drop(self, index: dict[str, str], user_id: str) -> None:
        for key in [key for key, value in index.items() if value == user_id]:
            del index[key]

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
        cleaned_domain = normalize_domain(domain)
        if not cleaned_domain:
            raise ValueError("Le domaine de la marque est requis.")
        if len(competitors) > 5:
            raise ValueError("Cinq concurrents maximum.")
        if len(queries) > 60:
            raise ValueError("Soixante requêtes maximum.")

        seen_domains: set[str] = set()
        wanted_competitors: list[tuple[str, str]] = []
        for name, raw_domain in competitors:
            competitor_domain = normalize_domain(raw_domain)
            if competitor_domain in seen_domains:
                raise ValueError(f"Le domaine {competitor_domain} est en double.")
            if competitor_domain == cleaned_domain:
                raise ValueError("Un concurrent ne peut pas partager le domaine de la marque.")
            seen_domains.add(competitor_domain)
            wanted_competitors.append((name.strip(), competitor_domain))

        seen_prompts: set[str] = set()
        wanted_queries: list[tuple[str, bool]] = []
        for prompt, active in queries:
            cleaned = " ".join(prompt.split())
            if cleaned in seen_prompts:
                raise ValueError("Deux requêtes sont identiques.")
            seen_prompts.add(cleaned)
            wanted_queries.append((cleaned, active))

        with self._session() as session, session.begin():
            row = self._workspace_row(session, user_id)
            if row is None:
                raise KeyError(user_id)
            # On garde les identifiants existants : l'historique des runs y reste rattaché.
            current_competitors = {item.domain: item for item in row.competitors}
            next_competitors: list[CompetitorRow] = []
            for index, (name, competitor_domain) in enumerate(wanted_competitors):
                item = current_competitors.pop(competitor_domain, None)
                if item is None:
                    item = CompetitorRow(id=uuid.uuid4().hex, domain=competitor_domain)
                item.name = name
                item.position = index
                next_competitors.append(item)

            current_queries = {item.prompt: item for item in row.queries}
            next_queries: list[QueryRow] = []
            for index, (prompt, active) in enumerate(wanted_queries):
                item = current_queries.pop(prompt, None)
                if item is None:
                    item = QueryRow(id=uuid.uuid4().hex, prompt=prompt)
                item.active = active
                item.position = index
                next_queries.append(item)

            # Supprimer d'abord les concurrents retirés, sinon la contrainte (espace, domaine) peut gêner.
            for item in current_competitors.values():
                session.delete(item)
            session.flush()

            row.name = workspace_name.strip()
            row.brand_name = brand_name.strip()
            row.domain = cleaned_domain
            row.sector = sector.strip()
            row.competitors = next_competitors
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

    def consume_questions(self, user_id: str, count: int) -> None:
        with self._session() as session, session.begin():
            row = self._workspace_row(session, user_id)
            if row is None:
                raise KeyError(user_id)
            self._roll_period(row)
            session.flush()
            # Incrément côté base : deux lancements simultanés ne s'écrasent pas.
            session.execute(
                update(WorkspaceRow)
                .where(WorkspaceRow.id == row.id)
                .values(questions_used=WorkspaceRow.questions_used + count)
            )

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
                )
                for run in runs
            )

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
