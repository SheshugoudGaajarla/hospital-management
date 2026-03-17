"""create lab orders table

Revision ID: 0010_create_lab_orders
Revises: 0009_add_patient_village_town
Create Date: 2026-03-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_create_lab_orders"
down_revision = "0009_add_patient_village_town"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_orders",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("op_visit_id", sa.Integer(), sa.ForeignKey("op_visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ordered"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lab_orders_op_visit_id", "lab_orders", ["op_visit_id"], unique=False)
    op.create_index("ix_lab_orders_created_at", "lab_orders", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lab_orders_created_at", table_name="lab_orders")
    op.drop_index("ix_lab_orders_op_visit_id", table_name="lab_orders")
    op.drop_table("lab_orders")
