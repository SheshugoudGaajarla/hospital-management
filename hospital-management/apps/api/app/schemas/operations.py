from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OpVisitStatus(str, Enum):
    WAITING = "waiting"
    IN_CONSULTATION = "in_consultation"
    LAB_PROCESSING = "lab_processing"
    PRESCRIPTION_READY = "prescription_ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BillStatus(str, Enum):
    PAID = "paid"
    UNPAID = "unpaid"
    REFUNDED = "refunded"


class OpVisitCreateRequest(BaseModel):
    patient_name: str = Field(min_length=2, max_length=120)
    village_town: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=0, le=120)
    weight_kg: float = Field(gt=0, le=300)
    bp: str = Field(min_length=3, max_length=20)
    doctor_name: str = Field(min_length=2, max_length=120)
    consultation_fee: float = Field(ge=0)
    consultation_payment_mode: str = Field(default="cash", min_length=3, max_length=30)

    @field_validator("bp")
    @classmethod
    def validate_bp(cls, value: str) -> str:
        normalized = value.strip().replace(" ", "")
        parts = normalized.split("/")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("BP must be in systolic/diastolic format, for example 120/80")
        return value.strip()


class OpVisitStatusUpdateRequest(BaseModel):
    status: OpVisitStatus


class OpVisitResponse(BaseModel):
    id: int
    patient_id: int
    uhid: str
    patient_name: str
    village_town: str
    age: int
    weight_kg: float
    bp: str
    token_no: int
    doctor_name: str
    consultation_fee: float
    consultation_payment_mode: str
    consultation_paid_at: datetime
    status: str
    visit_date: datetime


class ExpenseCreateRequest(BaseModel):
    category: str = Field(min_length=2, max_length=50)
    amount: float = Field(gt=0)
    notes: str | None = Field(default=None, max_length=255)


class ExpenseUpdateRequest(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=50)
    amount: float | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=255)


class ExpenseResponse(BaseModel):
    id: int
    category: str
    amount: float
    notes: str | None
    expense_date: datetime


class ExpenseSummaryResponse(BaseModel):
    total_amount: float


class MedicalBillCreateRequest(BaseModel):
    patient_id: int
    op_visit_id: int | None = None
    lab_fee: float = Field(default=0, ge=0)
    medicine_fee: float = Field(default=0, ge=0)
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    payment_mode: str = Field(default="cash", min_length=3, max_length=30)
    status: BillStatus = Field(default=BillStatus.UNPAID)


class MedicalBillUpdateRequest(BaseModel):
    status: BillStatus
    payment_mode: str | None = Field(default=None, min_length=3, max_length=30)
    refund_reason: str | None = Field(default=None, max_length=255)


class MedicalBillResponse(BaseModel):
    id: int
    invoice_no: str
    patient_id: int
    patient_name: str
    op_visit_id: int | None
    consultation_fee: float
    lab_fee: float
    medicine_fee: float
    discount: float
    tax: float
    net_amount: float
    payment_mode: str
    status: str
    paid_at: datetime | None
    refunded_at: datetime | None
    refund_reason: str | None
    created_at: datetime


class ConsultationCreateRequest(BaseModel):
    chief_complaint: str = Field(min_length=2, max_length=255)
    vitals: str | None = Field(default=None, max_length=500)
    diagnosis: str | None = Field(default=None, max_length=255)
    clinical_notes: str | None = Field(default=None, max_length=5000)
    advice: str | None = Field(default=None, max_length=5000)
    prescription_medicines: str | None = Field(default=None, max_length=5000)
    prescription_dosage: str | None = Field(default=None, max_length=5000)
    prescription_duration: str | None = Field(default=None, max_length=255)
    prescription_notes: str | None = Field(default=None, max_length=5000)
    follow_up_date: date | None = None


class ConsultationUpdateRequest(BaseModel):
    chief_complaint: str | None = Field(default=None, min_length=2, max_length=255)
    vitals: str | None = Field(default=None, max_length=500)
    diagnosis: str | None = Field(default=None, max_length=255)
    clinical_notes: str | None = Field(default=None, max_length=5000)
    advice: str | None = Field(default=None, max_length=5000)
    prescription_medicines: str | None = Field(default=None, max_length=5000)
    prescription_dosage: str | None = Field(default=None, max_length=5000)
    prescription_duration: str | None = Field(default=None, max_length=255)
    prescription_notes: str | None = Field(default=None, max_length=5000)
    follow_up_date: date | None = None


class ConsultationResponse(BaseModel):
    id: int
    op_visit_id: int
    chief_complaint: str
    vitals: str | None
    diagnosis: str | None
    clinical_notes: str | None
    advice: str | None
    prescription_medicines: str | None
    prescription_dosage: str | None
    prescription_duration: str | None
    prescription_notes: str | None
    follow_up_date: date | None
    created_at: datetime
    updated_at: datetime
