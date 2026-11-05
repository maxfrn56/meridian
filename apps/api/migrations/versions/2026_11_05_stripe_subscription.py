"""identifiants Stripe de l'abonnement

Revision ID: e7a1c3b94d20
Revises: c4d8a1e07b63
Create Date: 2026-11-05 12:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a1c3b94d20"
down_revision: Union[str, Sequence[str], None] = "c4d8a1e07b63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch:
        batch.add_column(sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch:
        batch.drop_column("stripe_subscription_id")
        batch.drop_column("stripe_customer_id")
