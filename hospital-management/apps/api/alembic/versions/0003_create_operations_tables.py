"""create operations tables

Revision ID: 0003_create_operations_tables
Revises: 0002_create_users
Create Date: 2026-03-01
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_create_operations_tables"
down_revision = "0002_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "op_visits",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_no", sa.Integer(), nullable=False),
        sa.Column("doctor_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="waiting"),
        sa.Column("visit_date", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_op_visits_created_at", "op_visits", ["created_at"], unique=False)

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("expense_date", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"], unique=False)

    op.create_table(
        "medical_bills",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("op_visit_id", sa.Integer(), sa.ForeignKey("op_visits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("consultation_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("lab_fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("medicine_fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_mode", sa.String(length=30), nullable=False, server_default="cash"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="paid"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_medical_bills_created_at", "medical_bills", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_medical_bills_created_at", table_name="medical_bills")
    op.drop_table("medical_bills")

    op.drop_index("ix_expenses_expense_date", table_name="expenses")
    op.drop_table("expenses")

    op.drop_index("ix_op_visits_created_at", table_name="op_visits")
    op.drop_table("op_visits")
