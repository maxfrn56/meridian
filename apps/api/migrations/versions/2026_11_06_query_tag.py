"""Étiquette libre sur chaque question suivie.

Revision ID: a1f6c2e84b90
Revises: d4c8a1b07e26
Create Date: 2026-11-06 16:50:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1f6c2e84b90"
down_revision: Union[str, Sequence[str], None] = "d4c8a1b07e26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("queries") as batch:
        batch.add_column(sa.Column("tag", sa.String(length=40), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("queries") as batch:
        batch.drop_column("tag")
