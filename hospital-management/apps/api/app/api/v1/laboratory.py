from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.rate_limit import limit_by_ip
from app.core.security import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.lab_order import LabOrder, LabOrderItem
from app.models.op_visit import OpVisit
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.laboratory import LabCatalogItemResponse, LabOrderCreateRequest, LabOrderItemResponse, LabOrderResponse, LabOrderStatus, LabOrderUpdateRequest
from app.services.lab_catalog import LAB_TEST_CATALOG, get_lab_catalog_item, match_lab_catalog_by_name

router = APIRouter(prefix="/api/v1/lab-orders", tags=["laboratory"])

ALLOWED_LAB_STATUS_TRANSITIONS: dict[str, set[str]] = {
    LabOrderStatus.ORDERED.value: {LabOrderStatus.COLLECTED.value, LabOrderStatus.PROCESSING.value},
    LabOrderStatus.COLLECTED.value: {LabOrderStatus.PROCESSING.value},
    LabOrderStatus.PROCESSING.value: {LabOrderStatus.COMPLETED.value},
    LabOrderStatus.COMPLETED.value: set(),
}


def _to_lab_order_response(order: LabOrder, visit: OpVisit, patient: Patient) -> LabOrderResponse:
    return LabOrderResponse(
        id=order.id,
        op_visit_id=order.op_visit_id,
        patient_name=patient.full_name,
        doctor_name=visit.doctor_name,
        status=order.status,
        payment_amount=float(order.payment_amount),
        payment_status=order.payment_status,
        payment_mode=order.payment_mode,
        result_summary=order.result_summary,
        items=[
            LabOrderItemResponse(
                id=item.id,
                test_code=item.test_code,
                test_name=item.test_name,
                department=item.department,
                category=item.category,
            )
            for item in order.items
        ],
        ordered_at=order.ordered_at,
        reported_at=order.reported_at,
        paid_at=order.paid_at,
    )


def _log_audit(db: Session, current_user: User, action: str, order_id: int, details: dict) -> None:
    db.add(
        AuditLog(
            user_id=current_user.id,
            module="laboratory",
            action=action,
            entity="lab_order",
            entity_id=order_id,
            details=details,
        )
    )


def _load_visit_and_patient(db: Session, op_visit_id: int) -> tuple[OpVisit, Patient]:
    visit = db.get(OpVisit, op_visit_id)
    if visit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OP visit not found")
    patient = db.get(Patient, visit.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return visit, patient


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
    body.extend((f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n").encode("ascii"))
    return bytes(body)


@router.get("/catalog", response_model=list[LabCatalogItemResponse])
def list_lab_catalog(
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)),
) -> list[LabCatalogItemResponse]:
    return [
        LabCatalogItemResponse(
            code=item.code,
            name=item.name,
            department=item.department,
            category=item.category,
        )
        for item in LAB_TEST_CATALOG
    ]


@router.post(
    "",
    response_model=list[LabOrderResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_lab_orders",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
) 
def create_lab_order(
    payload: LabOrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.LABORATORY)),
) -> list[LabOrderResponse]:
    visit, patient = _load_visit_and_patient(db, payload.op_visit_id)

    cleaned_codes: list[str] = []
    for raw_code in payload.test_codes:
        code = raw_code.strip().upper()
        if code and code not in cleaned_codes:
            cleaned_codes.append(code)

    custom_test_name = payload.custom_test_name.strip() if payload.custom_test_name else ""
    if not cleaned_codes and not custom_test_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select at least one lab test or enter a custom test")

    items_to_create: list[dict[str, str]] = []
    for code in cleaned_codes:
        catalog_item = get_lab_catalog_item(code)
        if catalog_item is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid lab test code: {code}")
        items_to_create.append(
            {
                "test_code": catalog_item.code,
                "test_name": catalog_item.name,
                "department": catalog_item.department,
                "category": catalog_item.category,
            }
        )

    if custom_test_name:
        custom_match = match_lab_catalog_by_name(custom_test_name)
        items_to_create.append(
            {
                "test_code": custom_match.code if custom_match else "CUSTOM",
                "test_name": custom_test_name,
                "department": custom_match.department if custom_match else "custom",
                "category": custom_match.category if custom_match else "Other",
            }
        )

    payment_status = payload.payment_status.strip().lower()
    if payment_status not in {"paid", "unpaid"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_status must be paid or unpaid")
    payment_mode = payload.payment_mode.strip().lower() if payload.payment_mode else None
    if payment_status == "paid" and not payment_mode:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_mode is required when payment is paid")

    order = LabOrder(
        op_visit_id=payload.op_visit_id,
        status=LabOrderStatus.ORDERED.value,
        payment_amount=round(payload.payment_amount, 2),
        payment_status=payment_status,
        payment_mode=payment_mode,
        paid_at=datetime.now() if payment_status == "paid" else None,
    )
    db.add(order)
    db.flush()
    for item in items_to_create:
        db.add(
            LabOrderItem(
                lab_order_id=order.id,
                test_code=item["test_code"],
                test_name=item["test_name"],
                department=item["department"],
                category=item["category"],
            )
        )

    _log_audit(
        db,
        current_user,
        action="create",
        order_id=order.id,
        details={
            "op_visit_id": payload.op_visit_id,
            "test_count": len(items_to_create),
            "tests": [item["test_name"] for item in items_to_create],
        },
    )

    db.commit()
    refreshed_order = db.execute(select(LabOrder).options(selectinload(LabOrder.items)).where(LabOrder.id == order.id)).scalar_one()
    return [_to_lab_order_response(refreshed_order, visit, patient)]


@router.get("", response_model=list[LabOrderResponse])
def list_lab_orders(
    op_visit_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.LABORATORY)),
) -> list[LabOrderResponse]:
    stmt = (
        select(LabOrder, OpVisit, Patient)
        .join(OpVisit, LabOrder.op_visit_id == OpVisit.id)
        .join(Patient, OpVisit.patient_id == Patient.id)
        .options(selectinload(LabOrder.items))
    )
    if current_user.role == UserRole.DOCTOR:
        stmt = stmt.where(OpVisit.doctor_name == current_user.full_name)
    if op_visit_id is not None:
        stmt = stmt.where(LabOrder.op_visit_id == op_visit_id)
    rows = db.execute(stmt.order_by(LabOrder.created_at.desc()).limit(100)).all()
    return [_to_lab_order_response(order, visit, patient) for order, visit, patient in rows]


@router.patch(
    "/{order_id}",
    response_model=LabOrderResponse,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="write_lab_orders_update",
                limit=settings.rate_limit_write_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def update_lab_order(
    order_id: int,
    payload: LabOrderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.LABORATORY)),
) -> LabOrderResponse:
    order = db.execute(select(LabOrder).options(selectinload(LabOrder.items)).where(LabOrder.id == order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab order not found")

    if payload.status is not None:
        allowed_next = ALLOWED_LAB_STATUS_TRANSITIONS.get(order.status, set())
        next_status = payload.status.value
        if next_status != order.status and next_status not in allowed_next:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {order.status} to {next_status}",
            )
        order.status = next_status
        if next_status == LabOrderStatus.COMPLETED.value:
            order.reported_at = datetime.now()
    if payload.result_summary is not None:
        order.result_summary = payload.result_summary.strip() or None
    if payload.payment_amount is not None:
        order.payment_amount = round(payload.payment_amount, 2)
    if payload.payment_status is not None:
        payment_status = payload.payment_status.strip().lower()
        if payment_status not in {"paid", "unpaid"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_status must be paid or unpaid")
        order.payment_status = payment_status
        if payment_status == "paid":
            order.paid_at = datetime.now() if order.paid_at is None else order.paid_at
        else:
            order.paid_at = None
    if payload.payment_mode is not None:
        order.payment_mode = payload.payment_mode.strip().lower() or None

    visit, patient = _load_visit_and_patient(db, order.op_visit_id)
    _log_audit(
        db,
        current_user,
        action="update",
        order_id=order.id,
        details={
            "status": order.status,
            "payment_status": order.payment_status,
            "payment_amount": float(order.payment_amount),
            "reported_at": order.reported_at.isoformat() if order.reported_at else None,
        },
    )

    db.commit()
    db.refresh(order)
    return _to_lab_order_response(order, visit, patient)


@router.get("/{order_id}/report.pdf")
def download_lab_report(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.LABORATORY, UserRole.DOCTOR)),
) -> Response:
    order = db.execute(select(LabOrder).options(selectinload(LabOrder.items)).where(LabOrder.id == order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab order not found")
    visit, patient = _load_visit_and_patient(db, order.op_visit_id)
    lines = [
        "Sri Laxmi Hospital",
        "Happy Mother and Safe Children",
        "Laboratory Report",
        f"Patient: {patient.full_name}",
        f"UHID: {patient.uhid}",
        f"Doctor: {visit.doctor_name}",
        f"Token: {visit.token_no}",
        f"Ordered At: {order.ordered_at.isoformat(sep=' ', timespec='seconds')}",
        f"Status: {order.status}",
        f"Payment: INR {float(order.payment_amount):.2f} / {order.payment_status}",
        "",
        "Tests:",
    ]
    for item in order.items:
        lines.append(f"- {item.test_name} ({item.category})")
    lines.extend(
        [
            "",
            f"Result Summary: {order.result_summary or '-'}",
            f"Reported At: {order.reported_at.isoformat(sep=' ', timespec='seconds') if order.reported_at else '-'}",
        ]
    )
    pdf_bytes = _simple_pdf(lines)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lab_order_{order.id}.pdf"'},
    )
