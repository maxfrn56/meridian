"""Tables de la base. Alembic génère les migrations à partir de ces classes."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Python 3.9 ne sait pas évaluer `datetime | None`. SQLAlchemy le fait au chargement des tables.
if sys.version_info < (3, 10):
    import ast

    import sqlalchemy.util.typing as _sa_typing
    from eval_type_backport.eval_type_backport import BackportTransformer

    _eval_expression = _sa_typing.eval_expression

    def _eval_annotation(expression, module_name, *, locals_=None, in_class=None):
        try:
            return _eval_expression(expression, module_name, locals_=locals_, in_class=in_class)
        except NameError:
            namespace = dict(sys.modules[module_name].__dict__)
            if in_class is not None:
                namespace.update(in_class.__dict__)
            if locals_:
                namespace.update(locals_)
            tree = ast.parse(expression, mode="eval")
            transformer = BackportTransformer(namespace, None)
            return transformer.eval_type(transformer.visit(tree))

    _sa_typing.eval_expression = _eval_annotation


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_verify_token_hash", "verify_token_hash"),
        Index("ix_users_reset_token_hash", "reset_token_hash"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16), default="client", server_default="client")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    session_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    verify_token_hash: Mapped[str] = mapped_column(String(64), default="", server_default="")
    verify_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    reset_token_hash: Mapped[str] = mapped_column(String(64), default="", server_default="")
    reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_verify_mail_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_reset_mail_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    workspace: Mapped[WorkspaceRow | None] = relationship(back_populates="user", cascade="all, delete-orphan")


class WorkspaceRow(Base):
    """Espace client. La marque suivie vit ici : un espace = une marque."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    brand_name: Mapped[str] = mapped_column(String(120), default="")
    domain: Mapped[str] = mapped_column(String(253), default="")
    sector: Mapped[str] = mapped_column(String(120), default="")
    plan_id: Mapped[str | None] = mapped_column(String(32), default=None)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), default=None)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), default=None)
    period_month: Mapped[str] = mapped_column(String(10), default="")
    questions_used: Mapped[int] = mapped_column(Integer, default=0)
    providers: Mapped[str] = mapped_column(String(80), default="openai,perplexity,gemini", server_default="openai,perplexity,gemini")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[UserRow] = relationship(back_populates="workspace")
    queries: Mapped[list[QueryRow]] = relationship(cascade="all, delete-orphan", order_by="QueryRow.position")


class QueryRow(Base):
    """Prompt suivi par le client."""

    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrackingRunRow(Base):
    """Une réponse d'un moteur à un prompt.

    query_id n'est pas une clé étrangère : l'historique reste quand le client supprime un prompt,
    et query_prompt garde le texte tel qu'il a été envoyé.
    """

    __tablename__ = "tracking_runs"
    __table_args__ = (Index("ix_tracking_runs_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    query_id: Mapped[str] = mapped_column(String(32), index=True)
    query_prompt: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(8))
    response_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # "llm" quand Claude a analysé la réponse ; vide sinon, l'analyse par mots-clés prend le relais.
    analysis_method: Mapped[str] = mapped_column(String(16), default="", server_default="")
    analysis_version: Mapped[str] = mapped_column(String(32), default="", server_default="")

    citations: Mapped[list[CitationRow]] = relationship(
        cascade="all, delete-orphan", order_by="CitationRow.position"
    )
    mentions: Mapped[list[MentionRow]] = relationship(
        cascade="all, delete-orphan", order_by="MentionRow.position"
    )


class CitationRow(Base):
    """Source citée par un moteur. Table à part pour agréger les domaines en SQL."""

    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("tracking_runs.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(253), index=True)
    title: Mapped[str | None] = mapped_column(Text, default=None)
    position: Mapped[int] = mapped_column(Integer)


class MentionRow(Base):
    """Marque nommée dans une réponse, relevée par l'analyse LLM. Toutes les marques, suivies ou non."""

    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("tracking_runs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    domain: Mapped[str] = mapped_column(String(253), default="")
    position: Mapped[int] = mapped_column(Integer)
    stance: Mapped[str] = mapped_column(String(16))
    sentiment: Mapped[float] = mapped_column(Float)
    excerpt: Mapped[str] = mapped_column(Text)


class AuditRow(Base):
    """Audit d'un site. Les scores sont en colonnes, le détail des contrôles en JSON."""

    __tablename__ = "audits"
    __table_args__ = (Index("ix_audits_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProspectRow(Base):
    __tablename__ = "prospects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company: Mapped[str] = mapped_column(String(120))
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    website: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    question: Mapped[str] = mapped_column(Text, default="")
    channel: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    sent_on: Mapped[str | None] = mapped_column(String(10), default=None)
    follow_up_on: Mapped[str | None] = mapped_column(String(10), default=None)
    meeting_on: Mapped[str | None] = mapped_column(String(10), default=None)
    amount_eur: Mapped[int | None] = mapped_column(Integer, default=None)
    next_step: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
