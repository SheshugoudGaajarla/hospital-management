"""create patients table

Revision ID: 0001_create_patients
Revises:
Create Date: 2026-02-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_create_patients"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("uhid", sa.String(length=30), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_patients_uhid", "patients", ["uhid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_patients_uhid", table_name="patients")
    op.drop_table("patients")
