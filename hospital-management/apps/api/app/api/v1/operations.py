from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limit_by_ip
from app.core.security import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.consultation import Consultation
from app.models.expense import Expense
from app.models.medical_bill import MedicalBill
from app.models.op_visit import OpVisit
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.operations import (
    ExpenseCreateRequest,
    ExpenseResponse,
    ExpenseSummaryResponse,
    ExpenseUpdateRequest,
    ConsultationCreateRequest,
    ConsultationResponse,
    ConsultationUpdateRequest,
    MedicalBillCreateRequest,
    MedicalBillResponse,
    MedicalBillUpdateRequest,
    OpVisitCreateRequest,
    OpVisitResponse,
    OpVisitStatus,
    OpVisitStatusUpdateRequest,
)

router = APIRouter(prefix="/api/v1", tags=["operations"])


ALLOWED_STATUS_TRANSITIONS = {
    OpVisitStatus.WAITING.value: {OpVisitStatus.IN_CONSULTATION.value, OpVisitStatus.CANCELLED.value},
    OpVisitStatus.IN_CONSULTATION.value: {
        OpVisitStatus.LAB_PROCESSING.value,
        OpVisitStatus.PRESCRIPTION_READY.value,
        OpVisitStatus.CANCELLED.value,
    },
    OpVisitStatus.LAB_PROCESSING.value: {OpVisitStatus.IN_CONSULTATION.value, OpVisitStatus.CANCELLED.value},
    OpVisitStatus.PRESCRIPTION_READY.value: {OpVisitStatus.COMPLETED.value, OpVisitStatus.CANCELLED.value},
    OpVisitStatus.COMPLETED.value: set(),
    OpVisitStatus.CANCELLED.value: set(),
}

BILL_STATUS_TRANSITIONS = {
    "unpaid": {"paid"},
    "paid": {"refunded"},
    "refunded": set(),
}


def _log_audit(
    db: Session,
    current_user: User,
    module: str,
    action: str,
    entity: str,
    entity_id: int | None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=current_user.id,
            module=module,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
        )
    )


def _to_op_response(visit: OpVisit, patient: Patient) -> OpVisitResponse:
    return OpVisitResponse(
        id=visit.id,
        patient_id=patient.id,
        uhid=patient.uhid,
        patient_name=patient.full_name,
        village_town=patient.village_town,
        age=visit.age,
        weight_kg=float(visit.weight_kg),
        bp=visit.bp,
        token_no=visit.token_no,
        doctor_name=visit.doctor_name,
        consultation_fee=float(visit.consultation_fee),
        consultation_payment_mode=visit.consultation_payment_mode,
        consultation_paid_at=visit.consultation_paid_at,
        status=visit.status,
        visit_date=visit.visit_date,
    )


def _to_expense_response(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        category=expense.category,
        amount=float(expense.amount),
        notes=expense.notes,
        expense_date=expense.expense_date,
    )


def _to_consultation_response(consultation: Consultation) -> ConsultationResponse:
    return ConsultationResponse(
        id=consultation.id,
        op_visit_id=consultation.op_visit_id,
        chief_complaint=consultation.chief_complaint,
        vitals=consultation.vitals,
        diagnosis=consultation.diagnosis,
        clinical_notes=consultation.clinical_notes,
        advice=consultation.advice,
        prescription_medicines=consultation.prescription_medicines,
        prescription_dosage=consultation.prescription_dosage,
        prescription_duration=consultation.prescription_duration,
        prescription_notes=consultation.prescription_notes,
        follow_up_date=consultation.follow_up_date,
        created_at=consultation.created_at,
        updated_at=consultation.updated_at,
    )


def _to_bill_response(bill: MedicalBill, patient_name: str) -> MedicalBillResponse:
    return MedicalBillResponse(
        id=bill.id,
        invoice_no=bill.invoice_no,
        patient_id=bill.patient_id,
        patient_name=patient_name,
        op_visit_id=bill.op_visit_id,
        consultation_fee=float(bill.consultation_fee),
        lab_fee=float(bill.lab_fee),
        medicine_fee=float(bill.medicine_fee),
        discount=float(bill.discount),
        tax=float(bill.tax),
        net_amount=float(bill.net_amount),
        payment_mode=bill.payment_mode,
        status=bill.status,
        paid_at=bill.paid_at,
        refunded_at=bill.refunded_at,
        refund_reason=bill.refund_reason,
        created_at=bill.created_at,
    )


def _next_invoice_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"INV-{today}-"
    stmt = (
        select(MedicalBill.invoice_no)
        .where(MedicalBill.invoice_no.like(f"{prefix}%"))
        .order_by(MedicalBill.invoice_no.desc())
        .limit(1)
    )
    last_invoice = db.execute(stmt).scalar_one_or_none()
    if not last_invoice:
        return f"{prefix}0001"
    last_serial = int(last_invoice.split("-")[-1])
    return f"{prefix}{last_serial + 1:04d}"


def _next_uhid(db: Session) -> str:
    prefix = "UH"
    stmt = (
        select(Patient.uhid)
        .where(Patient.uhid.like(f"{prefix}%"))
        .order_by(Patient.uhid.desc())
        .limit(1)
    )
    last_uhid = db.execute(stmt).scalar_one_or_none()
    if not last_uhid:
        return f"{prefix}000001"
    serial_text = str(last_uhid).replace(prefix, "", 1)
    serial = int(serial_text) if serial_text.isdigit() else 0
    return f"{prefix}{serial + 1:06d}"


def _ensure_doctor_visit_access(current_user: User, visit: OpVisit) -> None:
    if current_user.role == UserRole.DOCTOR and visit.doctor_name.strip().lower() != current_user.full_name.strip().lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only access your assigned OP visits")


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
        b"4 0 obj << /Length "
        + str(len(stream)).encode("ascii")
        + b" >> stream\n"
        + stream
        + b"\nendstream endobj\n"
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


@router.post(
    "/op-visits",
    response_model=OpVisitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_op_visits",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def create_op_visit(
    payload: OpVisitCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATIONS)),
) -> OpVisitResponse:
    patient = Patient(
        uhid=_next_uhid(db),
        full_name=payload.patient_name.strip(),
        village_town=payload.village_town.strip(),
        phone=None,
    )
    db.add(patient)
    db.flush()

    today = datetime.now().date()
    token_stmt = select(func.max(OpVisit.token_no)).where(func.date(OpVisit.visit_date) == today)
    last_token = db.execute(token_stmt).scalar_one_or_none() or 0

    visit = OpVisit(
        patient_id=patient.id,
        token_no=int(last_token) + 1,
        age=payload.age,
        weight_kg=round(payload.weight_kg, 2),
        bp=payload.bp.strip(),
        doctor_name=payload.doctor_name.strip(),
        consultation_fee=round(payload.consultation_fee, 2),
        consultation_payment_mode=payload.consultation_payment_mode.strip().lower(),
        status=OpVisitStatus.WAITING.value,
    )
    db.add(visit)
    db.flush()

    _log_audit(
        db,
        current_user,
        module="op",
        action="create",
        entity="op_visit",
        entity_id=visit.id,
        details={
            "token_no": visit.token_no,
            "patient_id": patient.id,
            "consultation_fee": float(visit.consultation_fee),
            "consultation_payment_mode": visit.consultation_payment_mode,
        },
    )

    db.commit()
    db.refresh(visit)
    return _to_op_response(visit, patient)


@router.patch(
    "/op-visits/{visit_id}/status",
    response_model=OpVisitResponse,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_op_status",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def update_op_visit_status(
    visit_id: int,
    payload: OpVisitStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> OpVisitResponse:
    visit = db.get(OpVisit, visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OP visit not found")
    _ensure_doctor_visit_access(current_user, visit)

    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(visit.status, set())
    if payload.status.value not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {visit.status} to {payload.status.value}",
        )

    if payload.status.value == OpVisitStatus.COMPLETED.value:
        consultation = db.execute(select(Consultation).where(Consultation.op_visit_id == visit_id)).scalar_one_or_none()
        if consultation is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consultation must be saved before completing visit",
            )

    visit.status = payload.status.value
    patient = db.get(Patient, visit.patient_id)
    _log_audit(
        db,
        current_user,
        module="op",
        action="status_update",
        entity="op_visit",
        entity_id=visit.id,
        details={"status": visit.status},
    )

    db.commit()
    db.refresh(visit)

    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return _to_op_response(visit, patient)


@router.get("/op-visits", response_model=list[OpVisitResponse])
def list_op_visits(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.MEDICAL, UserRole.LABORATORY)),
) -> list[OpVisitResponse]:
    stmt = select(OpVisit, Patient).join(Patient, OpVisit.patient_id == Patient.id)
    if current_user.role == UserRole.DOCTOR:
        stmt = stmt.where(OpVisit.doctor_name == current_user.full_name)
    stmt = stmt.order_by(OpVisit.created_at.desc()).limit(50)
    rows = db.execute(stmt).all()
    return [_to_op_response(visit, patient) for visit, patient in rows]


@router.get("/op-visits/{visit_id}/consultation", response_model=ConsultationResponse)
def get_consultation(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ConsultationResponse:
    visit = db.get(OpVisit, visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OP visit not found")
    _ensure_doctor_visit_access(current_user, visit)
    stmt = select(Consultation).where(Consultation.op_visit_id == visit_id)
    consultation = db.execute(stmt).scalar_one_or_none()
    if consultation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found for OP visit")
    return _to_consultation_response(consultation)


@router.post(
    "/op-visits/{visit_id}/consultation",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_consultation",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def create_consultation(
    visit_id: int,
    payload: ConsultationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ConsultationResponse:
    visit = db.get(OpVisit, visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OP visit not found")
    _ensure_doctor_visit_access(current_user, visit)

    existing = db.execute(select(Consultation).where(Consultation.op_visit_id == visit_id)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Consultation already exists for OP visit")

    consultation = Consultation(
        op_visit_id=visit_id,
        chief_complaint=payload.chief_complaint.strip(),
        vitals=payload.vitals.strip() if payload.vitals else None,
        diagnosis=payload.diagnosis.strip() if payload.diagnosis else None,
        clinical_notes=payload.clinical_notes.strip() if payload.clinical_notes else None,
        advice=payload.advice.strip() if payload.advice else None,
        prescription_medicines=payload.prescription_medicines.strip() if payload.prescription_medicines else None,
        prescription_dosage=payload.prescription_dosage.strip() if payload.prescription_dosage else None,
        prescription_duration=payload.prescription_duration.strip() if payload.prescription_duration else None,
        prescription_notes=payload.prescription_notes.strip() if payload.prescription_notes else None,
        follow_up_date=payload.follow_up_date,
    )
    db.add(consultation)
    db.flush()

    _log_audit(
        db,
        current_user,
        module="clinical",
        action="create",
        entity="consultation",
        entity_id=consultation.id,
        details={"op_visit_id": visit_id, "doctor_name": visit.doctor_name},
    )

    db.commit()
    db.refresh(consultation)
    return _to_consultation_response(consultation)


@router.patch(
    "/op-visits/{visit_id}/consultation",
    response_model=ConsultationResponse,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_consultation_update",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def update_consultation(
    visit_id: int,
    payload: ConsultationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ConsultationResponse:
    visit = db.get(OpVisit, visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OP visit not found")
    _ensure_doctor_visit_access(current_user, visit)
    consultation = db.execute(select(Consultation).where(Consultation.op_visit_id == visit_id)).scalar_one_or_none()
    if consultation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found for OP visit")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updates provided")

    if "chief_complaint" in updates and updates["chief_complaint"] is not None:
        consultation.chief_complaint = str(updates["chief_complaint"]).strip()
    if "vitals" in updates:
        raw_vitals = updates["vitals"]
        consultation.vitals = str(raw_vitals).strip() if raw_vitals else None
    if "diagnosis" in updates:
        raw_diagnosis = updates["diagnosis"]
        consultation.diagnosis = str(raw_diagnosis).strip() if raw_diagnosis else None
    if "clinical_notes" in updates:
        raw_notes = updates["clinical_notes"]
        consultation.clinical_notes = str(raw_notes).strip() if raw_notes else None
    if "advice" in updates:
        raw_advice = updates["advice"]
        consultation.advice = str(raw_advice).strip() if raw_advice else None
    if "prescription_medicines" in updates:
        raw_medicines = updates["prescription_medicines"]
        consultation.prescription_medicines = str(raw_medicines).strip() if raw_medicines else None
    if "prescription_dosage" in updates:
        raw_dosage = updates["prescription_dosage"]
        consultation.prescription_dosage = str(raw_dosage).strip() if raw_dosage else None
    if "prescription_duration" in updates:
        raw_duration = updates["prescription_duration"]
        consultation.prescription_duration = str(raw_duration).strip() if raw_duration else None
    if "prescription_notes" in updates:
        raw_rx_notes = updates["prescription_notes"]
        consultation.prescription_notes = str(raw_rx_notes).strip() if raw_rx_notes else None
    if "follow_up_date" in updates:
        consultation.follow_up_date = updates["follow_up_date"]

    _log_audit(
        db,
        current_user,
        module="clinical",
        action="update",
        entity="consultation",
        entity_id=consultation.id,
        details={"op_visit_id": visit_id, "updated_fields": sorted(updates.keys())},
    )

    db.commit()
    db.refresh(consultation)
    return _to_consultation_response(consultation)


@router.get("/op-visits/{visit_id}/consultation.pdf")
def download_consultation_pdf(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> Response:
    visit = db.get(OpVisit, visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OP visit not found")
    _ensure_doctor_visit_access(current_user, visit)

    consultation = db.execute(select(Consultation).where(Consultation.op_visit_id == visit_id)).scalar_one_or_none()
    if consultation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found for OP visit")

    patient = db.get(Patient, visit.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    lines = [
        "Sri Laxmi Hospital",
        "Happy Mother and Safe Children",
        "OP Consultation Sheet",
        f"Token: {visit.token_no}",
        f"Visit ID: {visit.id}",
        f"Visit Date: {visit.visit_date.isoformat(sep=' ', timespec='seconds')}",
        f"Doctor: {visit.doctor_name}",
        "",
        f"Patient: {patient.full_name}",
        f"Village/Town: {patient.village_town}",
        f"UHID: {patient.uhid}",
        f"Age/Weight/BP: {visit.age}y / {float(visit.weight_kg):.2f}kg / {visit.bp}",
        "",
        f"Chief Complaint: {consultation.chief_complaint}",
        f"Vitals: {consultation.vitals or '-'}",
        f"Diagnosis: {consultation.diagnosis or '-'}",
        f"Clinical Notes: {consultation.clinical_notes or '-'}",
        f"Advice: {consultation.advice or '-'}",
        "",
        "Prescription",
        f"Medicines: {consultation.prescription_medicines or '-'}",
        f"Dosage: {consultation.prescription_dosage or '-'}",
        f"Duration: {consultation.prescription_duration or '-'}",
        f"Prescription Notes: {consultation.prescription_notes or '-'}",
        "",
        f"Follow-up Date: {consultation.follow_up_date.isoformat() if consultation.follow_up_date else '-'}",
        f"Last Updated: {consultation.updated_at.isoformat(sep=' ', timespec='seconds')}",
    ]
    pdf_bytes = _simple_pdf(lines)
    filename = f"consultation_token_{visit.token_no}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_expenses",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def create_expense(
    payload: ExpenseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ExpenseResponse:
    expense = Expense(
        category=payload.category.strip(),
        amount=round(payload.amount, 2),
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(expense)
    db.flush()

    _log_audit(
        db,
        current_user,
        module="finance",
        action="create",
        entity="expense",
        entity_id=expense.id,
        details={"amount": float(expense.amount), "category": expense.category},
    )

    db.commit()
    db.refresh(expense)
    return _to_expense_response(expense)


@router.patch(
    "/expenses/{expense_id}",
    response_model=ExpenseResponse,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_expenses_update",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ExpenseResponse:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updates provided")

    if "category" in updates:
        expense.category = str(updates["category"]).strip()
    if "amount" in updates:
        expense.amount = round(float(updates["amount"]), 2)
    if "notes" in updates:
        raw_notes = updates["notes"]
        expense.notes = str(raw_notes).strip() if raw_notes else None

    _log_audit(
        db,
        current_user,
        module="finance",
        action="update",
        entity="expense",
        entity_id=expense.id,
        details={"updated_fields": sorted(updates.keys())},
    )

    db.commit()
    db.refresh(expense)
    return _to_expense_response(expense)


@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> list[ExpenseResponse]:
    stmt = select(Expense).order_by(Expense.expense_date.desc()).limit(50)
    expenses = db.execute(stmt).scalars().all()
    return [_to_expense_response(expense) for expense in expenses]


@router.get("/expenses/summary", response_model=ExpenseSummaryResponse)
def expenses_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ExpenseSummaryResponse:
    today = datetime.now().date()
    stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(func.date(Expense.expense_date) == today)
    total = db.execute(stmt).scalar_one()
    return ExpenseSummaryResponse(total_amount=float(total))


@router.post(
    "/medical-bills",
    response_model=MedicalBillResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_medical_bills",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def create_medical_bill(
    payload: MedicalBillCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEDICAL, UserRole.DOCTOR)),
) -> MedicalBillResponse:
    patient = db.get(Patient, payload.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    visit = None
    if payload.op_visit_id is not None:
        visit = db.get(OpVisit, payload.op_visit_id)
        if visit is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OP visit not found")

    subtotal = payload.lab_fee + payload.medicine_fee
    net_amount = max(0.0, subtotal - payload.discount + payload.tax)
    if payload.medicine_fee <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medicine fee must be greater than zero to create a medical bill",
        )
    if net_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Net payable must be greater than zero to create a medical bill",
        )

    bill = MedicalBill(
        patient_id=payload.patient_id,
        op_visit_id=payload.op_visit_id,
        invoice_no=_next_invoice_no(db),
        consultation_fee=0,
        lab_fee=round(payload.lab_fee, 2),
        medicine_fee=round(payload.medicine_fee, 2),
        discount=round(payload.discount, 2),
        tax=round(payload.tax, 2),
        net_amount=round(net_amount, 2),
        payment_mode=payload.payment_mode.strip().lower(),
        status=payload.status.value,
        paid_at=datetime.now() if payload.status.value == "paid" else None,
    )
    db.add(bill)
    db.flush()

    _log_audit(
        db,
        current_user,
        module="billing",
        action="create",
        entity="medical_bill",
        entity_id=bill.id,
        details={
            "invoice_no": bill.invoice_no,
            "patient_id": bill.patient_id,
            "net_amount": float(bill.net_amount),
            "status": bill.status,
        },
    )

    if payload.op_visit_id is not None and visit is not None:
        visit.status = OpVisitStatus.COMPLETED.value
        _log_audit(
            db,
            current_user,
            module="op",
            action="status_update",
            entity="op_visit",
            entity_id=visit.id,
            details={"status": visit.status, "reason": "medical_billing_completed"},
        )

    db.commit()
    db.refresh(bill)
    return _to_bill_response(bill, patient.full_name)


@router.patch(
    "/medical-bills/{bill_id}",
    response_model=MedicalBillResponse,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_medical_bills_update",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def update_medical_bill(
    bill_id: int,
    payload: MedicalBillUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEDICAL, UserRole.DOCTOR)),
) -> MedicalBillResponse:
    bill = db.get(MedicalBill, bill_id)
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical bill not found")

    next_status = payload.status.value
    if next_status != bill.status and next_status not in BILL_STATUS_TRANSITIONS.get(bill.status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {bill.status} to {next_status}",
        )

    if next_status == "refunded" and not payload.refund_reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refund_reason is required for refunds")

    bill.status = next_status
    if payload.payment_mode:
        bill.payment_mode = payload.payment_mode.strip().lower()
    if next_status == "paid" and bill.paid_at is None:
        bill.paid_at = datetime.now()
    if next_status == "refunded":
        bill.refunded_at = datetime.now()
        bill.refund_reason = payload.refund_reason.strip() if payload.refund_reason else None

    patient = db.get(Patient, bill.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    _log_audit(
        db,
        current_user,
        module="billing",
        action="update",
        entity="medical_bill",
        entity_id=bill.id,
        details={
            "invoice_no": bill.invoice_no,
            "status": bill.status,
            "payment_mode": bill.payment_mode,
            "refund_reason": bill.refund_reason,
        },
    )

    db.commit()
    db.refresh(bill)
    return _to_bill_response(bill, patient.full_name)


@router.get("/medical-bills", response_model=list[MedicalBillResponse])
def list_medical_bills(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEDICAL, UserRole.DOCTOR)),
) -> list[MedicalBillResponse]:
    stmt = (
        select(MedicalBill, Patient)
        .join(Patient, MedicalBill.patient_id == Patient.id)
        .order_by(MedicalBill.created_at.desc())
        .limit(50)
    )
    rows = db.execute(stmt).all()
    return [_to_bill_response(bill, patient.full_name) for bill, patient in rows]


@router.get("/medical-bills/{bill_id}/invoice.pdf")
def download_medical_bill_invoice(
    bill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEDICAL, UserRole.DOCTOR)),
) -> Response:
    bill = db.get(MedicalBill, bill_id)
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical bill not found")

    patient = db.get(Patient, bill.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    pdf_bytes = _simple_pdf(
        [
            "Sri Laxmi Hospital",
            "Happy Mother and Safe Children",
            f"Invoice: {bill.invoice_no}",
            f"Issued At: {bill.created_at.isoformat(sep=' ', timespec='seconds')}",
            "",
            f"Patient: {patient.full_name}",
            f"Phone: {patient.phone or '-'}",
            "",
            f"Lab Fee: INR {float(bill.lab_fee):.2f}",
            f"Medicine Fee: INR {float(bill.medicine_fee):.2f}",
            f"Discount: INR {float(bill.discount):.2f}",
            f"Tax: INR {float(bill.tax):.2f}",
            f"Net Amount: INR {float(bill.net_amount):.2f}",
            "",
            f"Payment Mode: {bill.payment_mode}",
            f"Status: {bill.status}",
        ]
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{bill.invoice_no}.pdf"'},
    )
