"""add payment fields to lab orders

Revision ID: 0012_add_lab_payment
Revises: 0011_refactor_lab_orders
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_add_lab_payment"
down_revision = "0011_refactor_lab_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_orders", sa.Column("payment_amount", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("lab_orders", sa.Column("payment_status", sa.String(length=20), nullable=False, server_default="unpaid"))
    op.add_column("lab_orders", sa.Column("payment_mode", sa.String(length=30), nullable=True))
    op.add_column("lab_orders", sa.Column("paid_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("lab_orders", "paid_at")
    op.drop_column("lab_orders", "payment_mode")
    op.drop_column("lab_orders", "payment_status")
    op.drop_column("lab_orders", "payment_amount")
