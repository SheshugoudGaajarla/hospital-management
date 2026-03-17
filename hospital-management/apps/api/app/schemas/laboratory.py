from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LabOrderStatus(str, Enum):
    ORDERED = "ordered"
    COLLECTED = "collected"
    PROCESSING = "processing"
    COMPLETED = "completed"


class LabOrderCreateRequest(BaseModel):
    op_visit_id: int
    test_codes: list[str] = Field(default_factory=list, max_length=20)
    custom_test_name: str | None = Field(default=None, min_length=2, max_length=120)
    payment_amount: float = Field(default=0, ge=0)
    payment_status: str = Field(default="unpaid", min_length=4, max_length=20)
    payment_mode: str | None = Field(default=None, min_length=3, max_length=30)


class LabOrderUpdateRequest(BaseModel):
    status: LabOrderStatus | None = None
    result_summary: str | None = Field(default=None, max_length=5000)
    payment_amount: float | None = Field(default=None, ge=0)
    payment_status: str | None = Field(default=None, min_length=4, max_length=20)
    payment_mode: str | None = Field(default=None, min_length=3, max_length=30)


class LabOrderItemResponse(BaseModel):
    id: int
    test_code: str
    test_name: str
    department: str
    category: str


class LabOrderResponse(BaseModel):
    id: int
    op_visit_id: int
    patient_name: str
    doctor_name: str
    status: str
    payment_amount: float
    payment_status: str
    payment_mode: str | None
    result_summary: str | None
    items: list[LabOrderItemResponse]
    ordered_at: datetime
    reported_at: datetime | None
    paid_at: datetime | None


class LabCatalogItemResponse(BaseModel):
    code: str
    name: str
    department: str
    category: str
