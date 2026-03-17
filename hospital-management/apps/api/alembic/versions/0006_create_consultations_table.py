"""create consultations table

Revision ID: 0006_create_consultations_table
Revises: 0005_add_invoice_fields_to_bills
Create Date: 2026-03-02
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_create_consultations_table"
down_revision = "0005_add_invoice_fields_to_bills"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consultations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("op_visit_id", sa.Integer(), sa.ForeignKey("op_visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chief_complaint", sa.String(length=255), nullable=False),
        sa.Column("vitals", sa.String(length=500), nullable=True),
        sa.Column("diagnosis", sa.String(length=255), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("advice", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("op_visit_id", name="uq_consultations_op_visit_id"),
    )
    op.create_index("ix_consultations_created_at", "consultations", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_consultations_created_at", table_name="consultations")
    op.drop_table("consultations")
