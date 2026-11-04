"""confirmation d'e-mail et mot de passe oublié

Revision ID: b7e1c0a9d4f2
Revises: 42864ff374c7
Create Date: 2026-11-04 15:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e1c0a9d4f2"
down_revision: Union[str, Sequence[str], None] = "42864ff374c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("verify_token_hash", sa.String(length=64), nullable=False, server_default=""))
        batch.add_column(sa.Column("verify_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("reset_token_hash", sa.String(length=64), nullable=False, server_default=""))
        batch.add_column(sa.Column("reset_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_verify_mail_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_reset_mail_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_verify_token_hash", "users", ["verify_token_hash"])
    op.create_index("ix_users_reset_token_hash", "users", ["reset_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_users_reset_token_hash", table_name="users")
    op.drop_index("ix_users_verify_token_hash", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("last_reset_mail_at")
        batch.drop_column("last_verify_mail_at")
        batch.drop_column("reset_expires_at")
        batch.drop_column("reset_token_hash")
        batch.drop_column("verify_expires_at")
        batch.drop_column("verify_token_hash")
        batch.drop_column("session_version")
        batch.drop_column("email_verified")
