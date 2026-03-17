from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MedicalBill(Base):
    __tablename__ = "medical_bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    op_visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("op_visits.id", ondelete="SET NULL"), nullable=True
    )
    invoice_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    consultation_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    lab_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    medicine_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="cash")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="paid")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    refund_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
