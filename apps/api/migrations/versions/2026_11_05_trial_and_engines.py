"""Essai de 7 jours et trois modèles choisis.

Revision ID: d4c8a1b07e26
Revises: c3b91e0a4d17
Create Date: 2026-11-05 16:20:00.000000

"""
from datetime import datetime, timedelta
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4c8a1b07e26"
down_revision: Union[str, Sequence[str], None] = "c3b91e0a4d17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch:
        batch.add_column(
            sa.Column(
                "providers",
                sa.String(length=80),
                nullable=False,
                server_default="openai,perplexity,gemini",
            )
        )
        batch.add_column(sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, created_at, plan_id FROM workspaces")).fetchall()
    for row in rows:
        if row.plan_id:
            continue
        created = row.created_at
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        if created is None:
            continue
        bind.execute(
            sa.text("UPDATE workspaces SET trial_ends_at = :ends WHERE id = :id"),
            {"ends": created + timedelta(days=7), "id": row.id},
        )


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch:
        batch.drop_column("trial_ends_at")
        batch.drop_column("providers")
