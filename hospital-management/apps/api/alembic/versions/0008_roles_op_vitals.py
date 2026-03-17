"""migrate roles and add op vitals fields

Revision ID: 0008_roles_op_vitals
Revises: 0007_add_consult_rx_fields
Create Date: 2026-03-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_roles_op_vitals"
down_revision = "0007_add_consult_rx_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("patients", "phone", existing_type=sa.String(length=20), nullable=True)

    op.add_column("op_visits", sa.Column("age", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("op_visits", sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("op_visits", sa.Column("bp", sa.String(length=20), nullable=False, server_default="NA"))

    op.alter_column("op_visits", "age", server_default=None)
    op.alter_column("op_visits", "weight_kg", server_default=None)
    op.alter_column("op_visits", "bp", server_default=None)

    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('doctor', 'admin', 'laboratory', 'medical', 'operations')")
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN role TYPE user_role
        USING (
            CASE role::text
                WHEN 'reception' THEN 'operations'
                WHEN 'billing' THEN 'medical'
                ELSE role::text
            END
        )::user_role
        """
    )
    op.execute("DROP TYPE user_role_old")


def downgrade() -> None:
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'reception', 'doctor', 'billing')")
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN role TYPE user_role
        USING (
            CASE role::text
                WHEN 'operations' THEN 'reception'
                WHEN 'medical' THEN 'billing'
                WHEN 'laboratory' THEN 'admin'
                ELSE role::text
            END
        )::user_role
        """
    )
    op.execute("DROP TYPE user_role_old")

    op.drop_column("op_visits", "bp")
    op.drop_column("op_visits", "weight_kg")
    op.drop_column("op_visits", "age")

    op.alter_column("patients", "phone", existing_type=sa.String(length=20), nullable=False)
