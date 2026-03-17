"""add village_town to patients

Revision ID: 0009_add_patient_village_town
Revises: 0008_roles_op_vitals
Create Date: 2026-03-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_add_patient_village_town"
down_revision = "0008_roles_op_vitals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("village_town", sa.String(length=120), nullable=False, server_default="Unknown"))
    op.alter_column("patients", "village_town", server_default=None)


def downgrade() -> None:
    op.drop_column("patients", "village_town")
