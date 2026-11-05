from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from models.schemas import PlanOut, SubscriptionOut
from store import Query, Workspace, store

TRIAL_DAYS = 7
TRIAL_PER_DAY = 10


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_eur: float
    questions_per_day: int
    detail: str


PLANS = (
    Plan(
        "essentiel",
        "Essentiel",
        79.9,
        20,
        "Vingt questions par jour, chaque jour du mois, chacune posée aux trois modèles choisis.",
    ),
    Plan(
        "croissance",
        "Croissance",
        189.9,
        100,
        "Cent questions par jour pour suivre un marché et ses concurrents.",
    ),
    Plan(
        "reference",
        "Référence",
        389.9,
        200,
        "Deux cents questions par jour pour couvrir plusieurs produits et plusieurs zones.",
    ),
)


def plan_by_id(plan_id: str | None) -> Plan | None:
    return next((item for item in PLANS if item.id == plan_id), None)


def trial_is_active(ends_at: datetime | None, plan_id: str | None) -> bool:
    """Sept jours sans forfait. Un forfait payé remplace l'essai."""
    if plan_id or ends_at is None:
        return False
    end = ends_at if ends_at.tzinfo else ends_at.replace(tzinfo=timezone.utc)
    return end > datetime.now(timezone.utc)


def trial_end_from(start: datetime | None = None) -> datetime:
    return (start or datetime.now(timezone.utc)) + timedelta(days=TRIAL_DAYS)


def questions_allowed(plan_id: str | None, trial_ends_at: datetime | None) -> int:
    plan = plan_by_id(plan_id)
    if plan is not None:
        return plan.questions_per_day
    if trial_is_active(trial_ends_at, plan_id):
        return TRIAL_PER_DAY
    raise ValueError("L'essai de 7 jours est terminé. Choisissez un forfait pour continuer à envoyer des questions.")


def _out(plan: Plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        name=plan.name,
        price_eur=plan.price_eur,
        questions_per_day=plan.questions_per_day,
        detail=plan.detail,
    )


def snapshot(workspace: Workspace) -> SubscriptionOut:
    fresh = store.current_workspace(workspace.user_id)
    current = plan_by_id(fresh.plan_id)
    active = trial_is_active(fresh.trial_ends_at, fresh.plan_id)
    try:
        allowance = questions_allowed(fresh.plan_id, fresh.trial_ends_at)
    except ValueError:
        allowance = 0
    remaining = max(0, allowance - fresh.questions_used)
    return SubscriptionOut(
        plan=_out(current) if current else None,
        questions_used=fresh.questions_used,
        questions_remaining=remaining,
        period_day=fresh.period_month,
        plans=[_out(item) for item in PLANS],
        trial_active=active,
        trial_ends_at=fresh.trial_ends_at,
    )


def quota_remaining(workspace: Workspace) -> int:
    fresh = store.current_workspace(workspace.user_id)
    allowance = questions_allowed(fresh.plan_id, fresh.trial_ends_at)
    return allowance - fresh.questions_used


def counted_queries(workspace: Workspace) -> list[Query]:
    """Les questions qui comptent : les premières de la liste, actives, dans la limite du jour."""
    active = [query for query in workspace.queries if query.active]
    try:
        allowance = questions_allowed(workspace.plan_id, workspace.trial_ends_at)
    except ValueError:
        return active
    return active[: max(0, allowance)]


def assert_quota(workspace: Workspace, questions: int) -> None:
    fresh = store.current_workspace(workspace.user_id)
    allowance = questions_allowed(fresh.plan_id, fresh.trial_ends_at)
    current = plan_by_id(fresh.plan_id)
    label = current.name if current else "L'essai"
    remaining = allowance - fresh.questions_used
    if questions > remaining:
        raise ValueError(
            f"{label} couvre {allowance} questions par jour. "
            f"Il en reste {max(0, remaining)} aujourd'hui, et ce lancement en demande {questions}."
        )


def activate(workspace: Workspace, plan_id: str) -> SubscriptionOut:
    if plan_by_id(plan_id) is None:
        raise ValueError("Forfait inconnu.")
    store.activate_plan(workspace.user_id, plan_id)
    return snapshot(workspace)
