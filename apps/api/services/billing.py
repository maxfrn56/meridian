from __future__ import annotations

from dataclasses import dataclass

from models.schemas import PlanOut, SubscriptionOut
from store import Workspace, store


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_eur: float
    questions_per_month: int
    detail: str


PLANS = (
    Plan(
        "essentiel",
        "Essentiel",
        79.9,
        5,
        "Cinq questions par mois, chacune posée sur OpenAI, Perplexity et Gemini.",
    ),
    Plan(
        "croissance",
        "Croissance",
        189.9,
        20,
        "Vingt questions par mois pour suivre un marché et ses concurrents.",
    ),
    Plan(
        "reference",
        "Référence",
        389.9,
        60,
        "Soixante questions par mois pour couvrir plusieurs produits et plusieurs zones.",
    ),
)


def plan_by_id(plan_id: str | None) -> Plan | None:
    return next((item for item in PLANS if item.id == plan_id), None)


def _out(plan: Plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        name=plan.name,
        price_eur=plan.price_eur,
        questions_per_month=plan.questions_per_month,
        detail=plan.detail,
    )


def snapshot(workspace: Workspace) -> SubscriptionOut:
    fresh = store.current_workspace(workspace.user_id)
    current = plan_by_id(fresh.plan_id)
    allowance = current.questions_per_month if current else 0
    remaining = max(0, allowance - fresh.questions_used)
    return SubscriptionOut(
        plan=_out(current) if current else None,
        questions_used=fresh.questions_used,
        questions_remaining=remaining,
        period_month=fresh.period_month,
        plans=[_out(item) for item in PLANS],
    )


def assert_quota(workspace: Workspace, questions: int) -> None:
    fresh = store.current_workspace(workspace.user_id)
    current = plan_by_id(fresh.plan_id)
    if current is None:
        raise ValueError("Choisissez un forfait avant de lancer des questions.")
    remaining = current.questions_per_month - fresh.questions_used
    if questions > remaining:
        raise ValueError(
            f"Le forfait {current.name} couvre {current.questions_per_month} questions ce mois-ci. "
            f"Il en reste {max(0, remaining)}, et ce lancement en demande {questions}."
        )


def activate(workspace: Workspace, plan_id: str) -> SubscriptionOut:
    if plan_by_id(plan_id) is None:
        raise ValueError("Forfait inconnu.")
    store.activate_plan(workspace.user_id, plan_id)
    return snapshot(workspace)
