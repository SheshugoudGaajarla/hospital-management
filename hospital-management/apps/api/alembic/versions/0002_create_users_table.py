"""create users table

Revision ID: 0002_create_users
Revises: 0001_create_patients
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0002_create_users"
down_revision = "0001_create_patients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role_enum = postgresql.ENUM(
        "admin",
        "reception",
        "doctor",
        "billing",
        name="user_role",
        create_type=False,
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    user_role_enum = postgresql.ENUM(
        "admin",
        "reception",
        "doctor",
        "billing",
        name="user_role",
        create_type=False,
    )
    user_role_enum.drop(op.get_bind(), checkfirst=True)
