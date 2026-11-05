from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

Provider = Literal["openai", "perplexity", "gemini"]
EntityType = Literal["brand", "competitor"]
CheckStatus = Literal["pass", "warn", "fail"]
Priority = Literal["P1", "P2", "P3"]
Category = Literal["technical", "semantic", "authority"]
RunStatus = Literal["completed", "failed"]
SourceMode = Literal["live", "mock"]
Stance = Literal["recommended", "compared", "mentioned", "discouraged"]
AnalysisMethod = Literal["llm", "keywords"]


class APIModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RegisterIn(APIModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(APIModel):
    email: str
    password: str


class EmailIn(APIModel):
    email: str = Field(min_length=5, max_length=160)


class TokenIn(APIModel):
    token: str = Field(min_length=20, max_length=256)


class ResetIn(APIModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=8, max_length=128)


class MessageOut(APIModel):
    message: str


ProspectStatus = Literal["a_contacter", "envoye", "relance", "rdv", "devis", "gagne", "perdu"]
ProspectChannel = Literal["email", "linkedin", "telephone"]


class ProspectIn(APIModel):
    company: str = Field(min_length=2, max_length=120)
    contact_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=160)
    website: str = Field(default="", max_length=200)
    city: str = Field(default="", max_length=80)
    question: str = Field(default="", max_length=2000)
    channel: ProspectChannel = "email"
    status: ProspectStatus = "a_contacter"
    sent_on: str | None = None
    follow_up_on: str | None = None
    meeting_on: str | None = None
    amount_eur: int | None = Field(default=None, ge=0, le=1_000_000)
    next_step: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def dates_are_real(self) -> "ProspectIn":
        for label, value in (
            ("envoi", self.sent_on),
            ("relance", self.follow_up_on),
            ("rendez-vous", self.meeting_on),
        ):
            if not value:
                continue
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as error:
                raise ValueError(f"La date de {label} doit être au format AAAA-MM-JJ.") from error
        return self


class ProspectOut(ProspectIn):
    id: str
    created_at: datetime
    updated_at: datetime


class ProspectSummary(APIModel):
    total: int
    to_contact: int
    waiting: int
    follow_ups_due: int
    meetings: int


class ProspectListOut(APIModel):
    items: list[ProspectOut]
    summary: ProspectSummary


class UserOut(APIModel):
    id: str
    name: str
    email: str
    role: Literal["client", "admin"] = "client"
    workspace_name: str
    brand_name: str
    domain: str


class AdminClientOut(APIModel):
    id: str
    name: str
    email: str
    email_verified: bool
    created_at: datetime
    workspace_name: str
    brand_name: str
    domain: str
    plan_id: str | None
    plan_name: str | None
    price_eur: float
    questions_used: int
    questions_per_month: int


class AdminPlanStatOut(APIModel):
    id: str
    name: str
    price_eur: float
    subscribers: int
    monthly_eur: float


class AdminOverviewOut(APIModel):
    accounts: int
    verified_accounts: int
    subscriptions: int
    monthly_revenue_eur: float
    questions_used: int
    plans: list[AdminPlanStatOut]
    clients: list[AdminClientOut]


class AuthOut(APIModel):
    token: str
    user: UserOut


class CompetitorIn(APIModel):
    name: str = Field(min_length=1, max_length=80)
    domain: str = Field(min_length=3, max_length=160)


class QueryIn(APIModel):
    prompt: str = Field(min_length=8, max_length=400)
    active: bool = True


class SettingsIn(APIModel):
    workspace_name: str = Field(min_length=2, max_length=80)
    brand_name: str = Field(min_length=1, max_length=80)
    domain: str = Field(min_length=3, max_length=160)
    sector: str = Field(min_length=2, max_length=80)
    competitors: list[CompetitorIn] = Field(default_factory=list)
    queries: list[QueryIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_limits(self) -> "SettingsIn":
        if len(self.competitors) > 5:
            raise ValueError("Cinq concurrents maximum.")
        if len(self.queries) > 60:
            raise ValueError("Soixante requêtes maximum.")
        return self


class CompetitorOut(APIModel):
    id: str
    name: str
    domain: str


class QueryOut(APIModel):
    id: str
    prompt: str
    active: bool


class SettingsOut(APIModel):
    workspace_name: str
    brand_name: str
    domain: str
    sector: str
    competitors: list[CompetitorOut]
    queries: list[QueryOut]


class CitationOut(APIModel):
    url: str
    domain: str
    title: str | None = None
    position: int


class MentionOut(APIModel):
    entity_name: str
    entity_type: EntityType
    position: int
    sentiment: float
    excerpt: str
    # Analyse LLM seulement : recommended | compared | mentioned | discouraged.
    stance: Stance | None = None


class TrackingRunOut(APIModel):
    id: str
    query_id: str
    query_prompt: str
    provider: Provider
    model: str
    status: RunStatus
    source: SourceMode
    cited: bool
    position: int | None = None
    sentiment: float | None = None
    error: str | None = None
    response_text: str
    citations: list[CitationOut]
    analysis: AnalysisMethod = "keywords"
    mentions: list[MentionOut]
    created_at: datetime


class QueryTrackingOut(APIModel):
    id: str
    prompt: str
    active: bool
    runs: dict[str, TrackingRunOut | None]


class TrackingOut(APIModel):
    queries: list[QueryTrackingOut]
    providers: list[Provider]
    llm_mode: Literal["mock", "live", "mixed"]


class RunIn(APIModel):
    query_ids: list[str] | None = None
    providers: list[Provider] | None = None


class TrendPoint(APIModel):
    week: str
    citation_rate: float
    share_of_voice: float
    geo_score: int | None = None


class SovSlice(APIModel):
    name: str
    kind: EntityType
    share: float
    mentions: int


class DomainStat(APIModel):
    domain: str
    citations: int
    runs_without_brand: int


class CompareProviderStat(APIModel):
    provider: Provider
    runs: int
    mentions: int
    visibility: float
    average_position: float | None
    sentiment: float | None
    own_source_rate: float
    sourced_rate: float


class CompareEntity(APIModel):
    name: str
    domain: str
    kind: EntityType
    mentions: int
    visibility: float
    average_position: float | None
    sentiment: float | None
    positive: int
    neutral: int
    negative: int
    own_source_rate: float
    sourced_rate: float
    by_provider: list[CompareProviderStat]


class CompareHit(APIModel):
    provider: Provider
    position: int
    sentiment: float


class CompareCell(APIModel):
    name: str
    hits: list[CompareHit]


class ComparePrompt(APIModel):
    query_id: str
    prompt: str
    runs: int
    brand_mentioned: bool
    cells: list[CompareCell]


class CompareSource(APIModel):
    domain: str
    citations: int
    runs: int
    runs_with_brand: int
    runs_without_brand: int
    owned_by: str | None
    entities: list[str]


class CompareGap(APIModel):
    title: str
    detail: str


class ComparisonOut(APIModel):
    brand_name: str
    domain: str
    week: str | None
    runs: int
    providers: list[Provider]
    entities: list[CompareEntity]
    prompts: list[ComparePrompt]
    sources: list[CompareSource]
    gaps: list[CompareGap]
    methodology: str


class Kpis(APIModel):
    geo_score: int | None
    geo_score_delta: int | None
    citation_rate: float | None
    citation_rate_delta: float | None
    share_of_voice: float | None
    share_of_voice_delta: float | None
    queries_tracked: int
    runs_completed: int


class OverviewOut(APIModel):
    workspace_name: str
    brand_name: str
    domain: str
    sector: str
    llm_mode: Literal["mock", "live", "mixed"]
    methodology: str
    kpis: Kpis
    trend: list[TrendPoint]
    share_of_voice: list[SovSlice]
    top_domains: list[DomainStat]


class CheckOut(APIModel):
    id: str
    label: str
    status: CheckStatus
    score: int
    detail: str


class RecommendationOut(APIModel):
    id: str
    priority: Priority
    category: Category
    title: str
    detail: str
    effort: Literal["low", "medium", "high"]
    steps: list[str] = Field(default_factory=list)


class AuditOut(APIModel):
    id: str
    url: str
    score: int
    heading_score: int
    schema_score: int
    factual_score: int
    crawler_score: int
    pages_crawled: list[str]
    checks: list[CheckOut]
    recommendations: list[RecommendationOut]
    created_at: datetime


class AuditHistoryPoint(APIModel):
    week: str
    score: int


class DiscoveredCompetitor(APIModel):
    name: str
    domain: str
    mentions: int
    providers: list[str]


class AuditResponse(APIModel):
    audit: AuditOut | None
    history: list[AuditHistoryPoint]
    discovered_competitors: list[DiscoveredCompetitor] = Field(default_factory=list)


class AuditRunIn(APIModel):
    url: str | None = None


class PlanOut(APIModel):
    id: str
    name: str
    price_eur: float
    questions_per_month: int
    detail: str


class SubscriptionOut(APIModel):
    plan: PlanOut | None
    questions_used: int
    questions_remaining: int
    period_month: str
    plans: list[PlanOut]


class SubscribeIn(APIModel):
    plan_id: str = Field(min_length=2, max_length=40)


class JobOut(APIModel):
    id: str
    kind: Literal["tracking", "audit"]
    status: Literal["queued", "running", "completed", "failed"]
    error: str | None = None
