"""Le compteur de questions porte le jour, plus le mois.

Revision ID: c3b91e0a4d17
Revises: 9fd57b4473a5
Create Date: 2026-11-05 15:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3b91e0a4d17"
down_revision: Union[str, Sequence[str], None] = "9fd57b4473a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch:
        batch.alter_column(
            "period_month",
            existing_type=sa.String(length=7),
            type_=sa.String(length=10),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch:
        batch.alter_column(
            "period_month",
            existing_type=sa.String(length=10),
            type_=sa.String(length=7),
            existing_nullable=False,
        )
