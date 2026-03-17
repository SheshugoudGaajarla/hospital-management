"""add consultation fee fields to op visits

Revision ID: 0013_add_op_consult_fee
Revises: 0012_add_lab_payment
Create Date: 2026-03-11 18:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0013_add_op_consult_fee"
down_revision: str | Sequence[str] | None = "0012_add_lab_payment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "op_visits",
        sa.Column("consultation_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "op_visits",
        sa.Column("consultation_payment_mode", sa.String(length=30), nullable=False, server_default="cash"),
    )
    op.add_column(
        "op_visits",
        sa.Column("consultation_paid_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_column("op_visits", "consultation_paid_at")
    op.drop_column("op_visits", "consultation_payment_mode")
    op.drop_column("op_visits", "consultation_fee")
