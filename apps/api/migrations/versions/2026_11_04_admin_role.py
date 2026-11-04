"""rôle administrateur

Revision ID: c4d8a1e07b63
Revises: b7e1c0a9d4f2
Create Date: 2026-11-04 16:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d8a1e07b63"
down_revision: Union[str, Sequence[str], None] = "b7e1c0a9d4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("role", sa.String(length=16), nullable=False, server_default=sa.text("'client'")))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("role")
