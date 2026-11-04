"""Chiffres de l'activité : comptes clients, forfaits et montant mensuel."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from db import session_scope
from models.schemas import AdminClientOut, AdminOverviewOut, AdminPlanStatOut
from models.tables import UserRow, WorkspaceRow
from services.billing import PLANS, plan_by_id


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def overview() -> AdminOverviewOut:
    with session_scope() as session:
        rows = session.execute(
            select(UserRow, WorkspaceRow)
            .outerjoin(WorkspaceRow, WorkspaceRow.user_id == UserRow.id)
            .where(UserRow.role != "admin")
            .order_by(UserRow.created_at.desc())
        ).all()
        extracted = [
            (
                user.id,
                user.name,
                user.email,
                user.email_verified,
                _aware(user.created_at),
                workspace.name if workspace else "",
                workspace.brand_name if workspace else "",
                workspace.domain if workspace else "",
                workspace.plan_id if workspace else None,
                workspace.questions_used if workspace else 0,
            )
            for user, workspace in rows
        ]

    counts = {plan.id: 0 for plan in PLANS}
    monthly = 0
    questions = 0
    verified = 0
    subscriptions = 0
    clients: list[AdminClientOut] = []
    for (
        user_id,
        name,
        email,
        email_verified,
        created_at,
        workspace_name,
        brand_name,
        domain,
        plan_id,
        questions_used,
    ) in extracted:
        if email_verified:
            verified += 1
        plan = plan_by_id(plan_id)
        allowance = 0
        price = 0
        plan_name = None
        if plan is not None:
            subscriptions += 1
            monthly += plan.price_eur
            counts[plan.id] += 1
            allowance = plan.questions_per_month
            price = plan.price_eur
            plan_name = plan.name
        questions += questions_used
        clients.append(
            AdminClientOut(
                id=user_id,
                name=name,
                email=email,
                email_verified=email_verified,
                created_at=created_at,
                workspace_name=workspace_name,
                brand_name=brand_name,
                domain=domain,
                plan_id=plan.id if plan else None,
                plan_name=plan_name,
                price_eur=price,
                questions_used=questions_used,
                questions_per_month=allowance,
            )
        )
    return AdminOverviewOut(
        accounts=len(extracted),
        verified_accounts=verified,
        subscriptions=subscriptions,
        monthly_revenue_eur=monthly,
        questions_used=questions,
        plans=[
            AdminPlanStatOut(
                id=plan.id,
                name=plan.name,
                price_eur=plan.price_eur,
                subscribers=counts[plan.id],
                monthly_eur=counts[plan.id] * plan.price_eur,
            )
            for plan in PLANS
        ],
        clients=clients,
    )
