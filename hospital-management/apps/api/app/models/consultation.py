from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    op_visit_id: Mapped[int] = mapped_column(
        ForeignKey("op_visits.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    chief_complaint: Mapped[str] = mapped_column(String(255), nullable=False)
    vitals: Mapped[str | None] = mapped_column(String(500), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    advice: Mapped[str | None] = mapped_column(Text(), nullable=True)
    prescription_medicines: Mapped[str | None] = mapped_column(Text(), nullable=True)
    prescription_dosage: Mapped[str | None] = mapped_column(Text(), nullable=True)
    prescription_duration: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prescription_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )
