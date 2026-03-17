"""add invoice and payment lifecycle fields to medical bills

Revision ID: 0005_add_invoice_fields_to_bills
Revises: 0004_create_audit_logs
Create Date: 2026-03-02
"""

from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision = "0005_add_invoice_fields_to_bills"
down_revision = "0004_create_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("medical_bills", sa.Column("invoice_no", sa.String(length=40), nullable=True))
    op.add_column("medical_bills", sa.Column("paid_at", sa.DateTime(), nullable=True))
    op.add_column("medical_bills", sa.Column("refunded_at", sa.DateTime(), nullable=True))
    op.add_column("medical_bills", sa.Column("refund_reason", sa.String(length=255), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, created_at FROM medical_bills ORDER BY created_at ASC, id ASC")
    ).all()

    counters: dict[str, int] = {}
    for row in rows:
        created_at = row.created_at if isinstance(row.created_at, datetime) else datetime.now()
        date_part = created_at.strftime("%Y%m%d")
        next_counter = counters.get(date_part, 0) + 1
        counters[date_part] = next_counter
        invoice_no = f"INV-{date_part}-{next_counter:04d}"
        bind.execute(
            sa.text("UPDATE medical_bills SET invoice_no = :invoice_no WHERE id = :id"),
            {"invoice_no": invoice_no, "id": row.id},
        )

    op.alter_column("medical_bills", "invoice_no", existing_type=sa.String(length=40), nullable=False)
    op.create_index("ix_medical_bills_invoice_no", "medical_bills", ["invoice_no"], unique=True)
    op.alter_column(
        "medical_bills",
        "status",
        existing_type=sa.String(length=30),
        server_default="unpaid",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "medical_bills",
        "status",
        existing_type=sa.String(length=30),
        server_default="paid",
        existing_nullable=False,
    )
    op.drop_index("ix_medical_bills_invoice_no", table_name="medical_bills")
    op.drop_column("medical_bills", "refund_reason")
    op.drop_column("medical_bills", "refunded_at")
    op.drop_column("medical_bills", "paid_at")
    op.drop_column("medical_bills", "invoice_no")
