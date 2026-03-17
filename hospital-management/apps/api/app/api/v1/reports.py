import csv
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.models.expense import Expense
from app.models.lab_order import LabOrder
from app.models.medical_bill import MedicalBill
from app.models.op_visit import OpVisit
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.reports import (
    DailySummaryResponse,
    DateRangeSummaryResponse,
    DoctorOpSummaryPoint,
    ExpenseCategoryPoint,
    OpSummaryResponse,
    TrendPoint,
)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _get_target_date(target_date: date | None) -> date:
    return target_date or datetime.now().date()


def _date_range(days: int) -> list[date]:
    safe_days = max(1, min(days, 30))
    end = datetime.now().date()
    start = end - timedelta(days=safe_days - 1)
    return [start + timedelta(days=offset) for offset in range(safe_days)]


def _revenue_for_day(db: Session, target_date: date) -> float:
    op_fee_stmt = select(func.coalesce(func.sum(OpVisit.consultation_fee), 0)).where(
        func.date(OpVisit.consultation_paid_at) == target_date
    )
    paid_lab_stmt = select(func.coalesce(func.sum(LabOrder.payment_amount), 0)).where(
        func.date(LabOrder.paid_at) == target_date,
        LabOrder.payment_status == "paid",
    )
    medical_stmt = select(func.coalesce(func.sum(MedicalBill.net_amount), 0)).where(
        func.date(MedicalBill.created_at) == target_date,
        MedicalBill.status == "paid",
    )
    op_fee = float(db.execute(op_fee_stmt).scalar_one())
    paid_lab = float(db.execute(paid_lab_stmt).scalar_one())
    medical = float(db.execute(medical_stmt).scalar_one())
    return round(op_fee + paid_lab + medical, 2)


def _revenue_for_range(db: Session, start_date: date, end_date: date) -> float:
    op_fee_stmt = select(func.coalesce(func.sum(OpVisit.consultation_fee), 0)).where(
        func.date(OpVisit.consultation_paid_at) >= start_date,
        func.date(OpVisit.consultation_paid_at) <= end_date,
    )
    paid_lab_stmt = select(func.coalesce(func.sum(LabOrder.payment_amount), 0)).where(
        func.date(LabOrder.paid_at) >= start_date,
        func.date(LabOrder.paid_at) <= end_date,
        LabOrder.payment_status == "paid",
    )
    medical_stmt = select(func.coalesce(func.sum(MedicalBill.net_amount), 0)).where(
        func.date(MedicalBill.created_at) >= start_date,
        func.date(MedicalBill.created_at) <= end_date,
        MedicalBill.status == "paid",
    )
    op_fee = float(db.execute(op_fee_stmt).scalar_one())
    paid_lab = float(db.execute(paid_lab_stmt).scalar_one())
    medical = float(db.execute(medical_stmt).scalar_one())
    return round(op_fee + paid_lab + medical, 2)


def _daily_summary_data(db: Session, target_date: date) -> DailySummaryResponse:
    op_count_stmt = select(func.count(OpVisit.id)).where(func.date(OpVisit.visit_date) == target_date)
    pending_stmt = select(func.count(OpVisit.id)).where(
        func.date(OpVisit.visit_date) == target_date,
        OpVisit.status.in_(["waiting", "in_consultation", "lab_processing", "prescription_ready"]),
    )
    expenses_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        func.date(Expense.expense_date) == target_date
    )

    op_count = int(db.execute(op_count_stmt).scalar_one())
    pending_queue = int(db.execute(pending_stmt).scalar_one())
    revenue = _revenue_for_day(db, target_date)
    expenses = float(db.execute(expenses_stmt).scalar_one())

    return DailySummaryResponse(
        date=target_date,
        op_count=op_count,
        pending_queue=pending_queue,
        revenue=round(revenue, 2),
        expenses=round(expenses, 2),
        net_collection=round(revenue - expenses, 2),
    )


def _op_summary_data(db: Session, target_date: date) -> OpSummaryResponse:
    stmt = (
        select(OpVisit.status, func.count(OpVisit.id))
        .where(func.date(OpVisit.visit_date) == target_date)
        .group_by(OpVisit.status)
    )
    rows = db.execute(stmt).all()

    counts = {str(status): int(count) for status, count in rows}
    waiting = counts.get("waiting", 0)
    in_consultation = counts.get("in_consultation", 0)
    lab_processing = counts.get("lab_processing", 0)
    prescription_ready = counts.get("prescription_ready", 0)
    completed = counts.get("completed", 0)
    cancelled = counts.get("cancelled", 0)

    return OpSummaryResponse(
        date=target_date,
        total=waiting + in_consultation + lab_processing + prescription_ready + completed + cancelled,
        waiting=waiting,
        in_consultation=in_consultation,
        lab_processing=lab_processing,
        prescription_ready=prescription_ready,
        completed=completed,
        cancelled=cancelled,
    )


def _csv_response(filename: str, rows: list[list[str]]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _validate_date_range(start_date: date, end_date: date, max_days: int = 92) -> tuple[date, date]:
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")
    if (end_date - start_date).days + 1 > max_days:
        raise HTTPException(status_code=400, detail=f"Date range cannot exceed {max_days} days")
    return start_date, end_date


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf(lines: list[str]) -> bytes:
    y = 790
    content_lines = ["BT", "/F1 12 Tf", f"50 {y} Td"]
    first = True
    for line in lines:
        escaped = _pdf_escape(line)
        if not first:
            content_lines.append("0 -18 Td")
        content_lines.append(f"({escaped}) Tj")
        first = False
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("utf-8")

    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        (
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj\n"
        ).encode("utf-8")
    )
    objects.append(
        b"4 0 obj << /Length " + str(len(stream)).encode("ascii") + b" >> stream\n" + stream + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body = bytearray(header)
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body.extend(obj)

    xref_start = len(body)
    body.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    body.extend(
        (
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(body)


@router.get("/daily-summary", response_model=DailySummaryResponse)
def daily_summary(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> DailySummaryResponse:
    return _daily_summary_data(db, _get_target_date(report_date))


@router.get("/revenue-trend", response_model=list[TrendPoint])
def revenue_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> list[TrendPoint]:
    dates = _date_range(days)
    return [TrendPoint(date=day, value=_revenue_for_day(db, day)) for day in dates]


@router.get("/expense-trend", response_model=list[TrendPoint])
def expense_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> list[TrendPoint]:
    dates = _date_range(days)
    start_date = dates[0]

    stmt = (
        select(func.date(Expense.expense_date), func.coalesce(func.sum(Expense.amount), 0))
        .where(func.date(Expense.expense_date) >= start_date)
        .group_by(func.date(Expense.expense_date))
    )
    rows = db.execute(stmt).all()
    value_map = {row[0]: float(row[1]) for row in rows}

    return [TrendPoint(date=day, value=round(value_map.get(day, 0.0), 2)) for day in dates]


@router.get("/op-summary", response_model=OpSummaryResponse)
def op_summary(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> OpSummaryResponse:
    return _op_summary_data(db, _get_target_date(report_date))


@router.get("/date-range-summary", response_model=DateRangeSummaryResponse)
def date_range_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> DateRangeSummaryResponse:
    safe_start, safe_end = _validate_date_range(start_date, end_date)

    op_count_stmt = select(func.count(OpVisit.id)).where(
        func.date(OpVisit.visit_date) >= safe_start, func.date(OpVisit.visit_date) <= safe_end
    )
    expense_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        func.date(Expense.expense_date) >= safe_start,
        func.date(Expense.expense_date) <= safe_end,
    )

    op_count = int(db.execute(op_count_stmt).scalar_one())
    revenue = _revenue_for_range(db, safe_start, safe_end)
    expenses = float(db.execute(expense_stmt).scalar_one())
    total_days = (safe_end - safe_start).days + 1

    return DateRangeSummaryResponse(
        start_date=safe_start,
        end_date=safe_end,
        total_days=total_days,
        op_count=op_count,
        revenue=round(revenue, 2),
        expenses=round(expenses, 2),
        net_collection=round(revenue - expenses, 2),
    )


@router.get("/doctor-op-summary", response_model=list[DoctorOpSummaryPoint])
def doctor_op_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> list[DoctorOpSummaryPoint]:
    safe_start, safe_end = _validate_date_range(start_date, end_date)

    completed_count = func.sum(case((OpVisit.status == "completed", 1), else_=0))
    stmt = (
        select(OpVisit.doctor_name, func.count(OpVisit.id), completed_count)
        .where(func.date(OpVisit.visit_date) >= safe_start, func.date(OpVisit.visit_date) <= safe_end)
        .group_by(OpVisit.doctor_name)
        .order_by(func.count(OpVisit.id).desc(), OpVisit.doctor_name.asc())
    )
    rows = db.execute(stmt).all()
    return [
        DoctorOpSummaryPoint(
            doctor_name=str(doctor_name),
            total_visits=int(total),
            completed_visits=int(completed or 0),
        )
        for doctor_name, total, completed in rows
    ]


@router.get("/expense-category-summary", response_model=list[ExpenseCategoryPoint])
def expense_category_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> list[ExpenseCategoryPoint]:
    safe_start, safe_end = _validate_date_range(start_date, end_date)

    stmt = (
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0))
        .where(func.date(Expense.expense_date) >= safe_start, func.date(Expense.expense_date) <= safe_end)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc(), Expense.category.asc())
    )
    rows = db.execute(stmt).all()
    return [ExpenseCategoryPoint(category=str(category), amount=round(float(amount), 2)) for category, amount in rows]


@router.get("/daily-summary.csv")
def daily_summary_csv(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> StreamingResponse:
    summary = _daily_summary_data(db, _get_target_date(report_date))
    rows = [
        ["date", "op_count", "pending_queue", "revenue", "expenses", "net_collection"],
        [
            summary.date.isoformat(),
            str(summary.op_count),
            str(summary.pending_queue),
            f"{summary.revenue:.2f}",
            f"{summary.expenses:.2f}",
            f"{summary.net_collection:.2f}",
        ],
    ]
    return _csv_response(f"daily-summary-{summary.date.isoformat()}.csv", rows)


@router.get("/op-visits.csv")
def op_visits_csv(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> StreamingResponse:
    target_date = _get_target_date(report_date)
    stmt = (
        select(OpVisit, Patient)
        .join(Patient, OpVisit.patient_id == Patient.id)
        .where(func.date(OpVisit.visit_date) == target_date)
        .order_by(OpVisit.token_no.asc())
    )
    rows_data = db.execute(stmt).all()

    rows = [[
        "token_no",
        "uhid",
        "patient_name",
        "village_town",
        "age",
        "weight_kg",
        "bp",
        "doctor_name",
        "consultation_fee",
        "consultation_payment_mode",
        "status",
        "visit_date",
    ]]
    for visit, patient in rows_data:
        rows.append(
            [
                str(visit.token_no),
                patient.uhid,
                patient.full_name,
                patient.village_town,
                str(visit.age),
                f"{float(visit.weight_kg):.2f}",
                visit.bp,
                visit.doctor_name,
                f"{float(visit.consultation_fee):.2f}",
                visit.consultation_payment_mode,
                visit.status,
                visit.visit_date.isoformat(sep=" ", timespec="seconds"),
            ]
        )

    return _csv_response(f"op-visits-{target_date.isoformat()}.csv", rows)


@router.get("/expenses.csv")
def expenses_csv(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> StreamingResponse:
    target_date = _get_target_date(report_date)
    stmt = (
        select(Expense)
        .where(func.date(Expense.expense_date) == target_date)
        .order_by(Expense.expense_date.asc())
    )
    expenses = db.execute(stmt).scalars().all()

    rows = [["category", "amount", "notes", "expense_date"]]
    for expense in expenses:
        rows.append(
            [
                expense.category,
                f"{float(expense.amount):.2f}",
                expense.notes or "",
                expense.expense_date.isoformat(sep=" ", timespec="seconds"),
            ]
        )

    return _csv_response(f"expenses-{target_date.isoformat()}.csv", rows)


@router.get("/medical-bills.csv")
def medical_bills_csv(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> StreamingResponse:
    target_date = _get_target_date(report_date)
    stmt = (
        select(MedicalBill, Patient)
        .join(Patient, MedicalBill.patient_id == Patient.id)
        .where(func.date(MedicalBill.created_at) == target_date)
        .order_by(MedicalBill.created_at.asc())
    )
    rows_data = db.execute(stmt).all()

    rows = [["bill_id", "patient_name", "net_amount", "payment_mode", "status", "created_at"]]
    for bill, patient in rows_data:
        rows.append(
            [
                str(bill.id),
                patient.full_name,
                f"{float(bill.net_amount):.2f}",
                bill.payment_mode,
                bill.status,
                bill.created_at.isoformat(sep=" ", timespec="seconds"),
            ]
        )

    return _csv_response(f"medical-bills-{target_date.isoformat()}.csv", rows)


@router.get("/daily-summary.pdf")
def daily_summary_pdf(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)
    ),
) -> Response:
    target_date = _get_target_date(report_date)
    summary = _daily_summary_data(db, target_date)
    op = _op_summary_data(db, target_date)

    pdf_bytes = _simple_pdf(
        [
            "Sri Laxmi Hospital",
            "Happy Mother and Safe Children",
            f"Date: {summary.date.isoformat()}",
            "",
            "Daily Financial Summary",
            f"Revenue: INR {summary.revenue:.2f}",
            f"Expenses: INR {summary.expenses:.2f}",
            f"Net Collection: INR {summary.net_collection:.2f}",
            "",
            "OP Summary",
            f"Total Visits: {op.total}",
            f"Waiting: {op.waiting}",
            f"In Consultation: {op.in_consultation}",
            f"Completed: {op.completed}",
            f"Cancelled: {op.cancelled}",
        ]
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="daily-summary-{target_date.isoformat()}.pdf"'},
    )
