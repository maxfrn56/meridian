"""réunit les migrations Stripe et analyse LLM

Revision ID: b8e4d1a06c53
Revises: e7a1c3b94d20, 2967476eea38
Create Date: 2026-11-05 12:40:00.000000

"""
from typing import Sequence, Union

revision: str = "b8e4d1a06c53"
down_revision: Union[str, Sequence[str], None] = ("e7a1c3b94d20", "2967476eea38")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
