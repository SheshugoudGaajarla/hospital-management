"""refactor lab orders into header and items

Revision ID: 0011_refactor_lab_orders
Revises: 0010_create_lab_orders
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_refactor_lab_orders"
down_revision = "0010_create_lab_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("lab_orders", "lab_orders_legacy")
    op.drop_index("ix_lab_orders_op_visit_id", table_name="lab_orders_legacy")
    op.drop_index("ix_lab_orders_created_at", table_name="lab_orders_legacy")

    op.create_table(
        "lab_orders",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("op_visit_id", sa.Integer(), sa.ForeignKey("op_visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ordered"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lab_orders_op_visit_id", "lab_orders", ["op_visit_id"], unique=False)
    op.create_index("ix_lab_orders_created_at", "lab_orders", ["created_at"], unique=False)

    op.create_table(
        "lab_order_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("lab_order_id", sa.Integer(), sa.ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_code", sa.String(length=40), nullable=False),
        sa.Column("test_name", sa.String(length=120), nullable=False),
        sa.Column("department", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lab_order_items_lab_order_id", "lab_order_items", ["lab_order_id"], unique=False)

    connection = op.get_bind()
    legacy_rows = connection.execute(
        sa.text(
            """
            SELECT id, op_visit_id, test_name, status, result_summary, ordered_at, reported_at, created_at
            FROM lab_orders_legacy
            ORDER BY id
            """
        )
    ).mappings().all()

    for row in legacy_rows:
        new_order_id = connection.execute(
            sa.text(
                """
                INSERT INTO lab_orders (op_visit_id, status, result_summary, ordered_at, reported_at, created_at)
                VALUES (:op_visit_id, :status, :result_summary, :ordered_at, :reported_at, :created_at)
                RETURNING id
                """
            ),
            {
                "op_visit_id": row["op_visit_id"],
                "status": row["status"],
                "result_summary": row["result_summary"],
                "ordered_at": row["ordered_at"],
                "reported_at": row["reported_at"],
                "created_at": row["created_at"],
            },
        ).scalar_one()

        connection.execute(
            sa.text(
                """
                INSERT INTO lab_order_items (lab_order_id, test_code, test_name, department, category, created_at)
                VALUES (:lab_order_id, :test_code, :test_name, :department, :category, :created_at)
                """
            ),
            {
                "lab_order_id": new_order_id,
                "test_code": row["test_name"].upper().replace(" ", "_"),
                "test_name": row["test_name"],
                "department": "custom",
                "category": "Other",
                "created_at": row["created_at"],
            },
        )

    op.drop_table("lab_orders_legacy")


def downgrade() -> None:
    op.create_table(
        "lab_orders_legacy",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("op_visit_id", sa.Integer(), sa.ForeignKey("op_visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ordered"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT lo.id AS order_id, lo.op_visit_id, lo.status, lo.result_summary, lo.ordered_at, lo.reported_at, lo.created_at,
                   loi.test_name
            FROM lab_orders lo
            JOIN lab_order_items loi ON loi.lab_order_id = lo.id
            ORDER BY lo.id, loi.id
            """
        )
    ).mappings().all()

    for row in rows:
        connection.execute(
            sa.text(
                """
                INSERT INTO lab_orders_legacy (op_visit_id, test_name, status, result_summary, ordered_at, reported_at, created_at)
                VALUES (:op_visit_id, :test_name, :status, :result_summary, :ordered_at, :reported_at, :created_at)
                """
            ),
            {
                "op_visit_id": row["op_visit_id"],
                "test_name": row["test_name"],
                "status": row["status"],
                "result_summary": row["result_summary"],
                "ordered_at": row["ordered_at"],
                "reported_at": row["reported_at"],
                "created_at": row["created_at"],
            },
        )

    op.drop_index("ix_lab_order_items_lab_order_id", table_name="lab_order_items")
    op.drop_table("lab_order_items")
    op.drop_index("ix_lab_orders_created_at", table_name="lab_orders")
    op.drop_index("ix_lab_orders_op_visit_id", table_name="lab_orders")
    op.drop_table("lab_orders")
    op.rename_table("lab_orders_legacy", "lab_orders")
