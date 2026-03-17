"""add prescription fields to consultations

Revision ID: 0007_add_consult_rx_fields
Revises: 0006_create_consultations_table
Create Date: 2026-03-02
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_add_consult_rx_fields"
down_revision = "0006_create_consultations_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultations", sa.Column("prescription_medicines", sa.Text(), nullable=True))
    op.add_column("consultations", sa.Column("prescription_dosage", sa.Text(), nullable=True))
    op.add_column("consultations", sa.Column("prescription_duration", sa.String(length=255), nullable=True))
    op.add_column("consultations", sa.Column("prescription_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("consultations", "prescription_notes")
    op.drop_column("consultations", "prescription_duration")
    op.drop_column("consultations", "prescription_dosage")
    op.drop_column("consultations", "prescription_medicines")
