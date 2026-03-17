from datetime import date

from pydantic import BaseModel


class TrendPoint(BaseModel):
    date: date
    value: float


class DailySummaryResponse(BaseModel):
    date: date
    op_count: int
    pending_queue: int
    revenue: float
    expenses: float
    net_collection: float


class OpSummaryResponse(BaseModel):
    date: date
    total: int
    waiting: int
    in_consultation: int
    lab_processing: int
    prescription_ready: int
    completed: int
    cancelled: int


class DateRangeSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_days: int
    op_count: int
    revenue: float
    expenses: float
    net_collection: float


class DoctorOpSummaryPoint(BaseModel):
    doctor_name: str
    total_visits: int
    completed_visits: int


class ExpenseCategoryPoint(BaseModel):
    category: str
    amount: float
