from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LabOrder(Base):
    __tablename__ = "lab_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    op_visit_id: Mapped[int] = mapped_column(ForeignKey("op_visits.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ordered")
    payment_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unpaid")
    payment_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    items: Mapped[list["LabOrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LabOrderItem.id",
    )


class LabOrderItem(Base):
    __tablename__ = "lab_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_order_id: Mapped[int] = mapped_column(ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    test_code: Mapped[str] = mapped_column(String(40), nullable=False)
    test_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    order: Mapped[LabOrder] = relationship(back_populates="items")
