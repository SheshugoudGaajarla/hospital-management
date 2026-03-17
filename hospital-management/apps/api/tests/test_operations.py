from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.core.security import hash_password
from app.core.metrics import metrics_store
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models import audit_log as _audit_models
from app.models import consultation as _consultation_models
from app.models import expense as _expense_models
from app.models import lab_order as _lab_order_models
from app.models import medical_bill as _bill_models
from app.models import op_visit as _visit_models
from app.models import patient as _patient_models
from app.models import user as _user_models
from app.main import app
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module() -> None:
    _ = (
        _audit_models,
        _consultation_models,
        _expense_models,
        _lab_order_models,
        _bill_models,
        _visit_models,
        _patient_models,
        _user_models,
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    rate_limiter.reset()
    metrics_store.reset()

client = TestClient(app)


def _bootstrap_and_login() -> str:
    bootstrap_response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "username": "admin",
            "full_name": "System Admin",
            "password": "admin1234",
        },
    )
    assert bootstrap_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin1234"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _create_doctor_user(username: str, full_name: str, password: str) -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            User(
                username=username,
                full_name=full_name,
                role=UserRole.DOCTOR,
                password_hash=hash_password(password),
            )
        )
        db.commit()
    finally:
        db.close()


def _create_user(username: str, full_name: str, password: str, role: UserRole) -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            User(
                username=username,
                full_name=full_name,
                role=role,
                password_hash=hash_password(password),
            )
        )
        db.commit()
    finally:
        db.close()


def _login(username: str, password: str) -> str:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def test_operations_crud_and_validations() -> None:
    token = _bootstrap_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    _create_user("doctor_mehta", "Dr. Mehta", "doctor1234", UserRole.DOCTOR)
    _create_user("lab_user", "Lab User", "lab123456", UserRole.LABORATORY)
    lab_headers = {"Authorization": f"Bearer {_login('lab_user', 'lab123456')}"}

    create_visit = client.post(
        "/api/v1/op-visits",
        headers=headers,
        json={
            "patient_name": "Anita Rao",
            "village_town": "Narsampet",
            "age": 31,
            "weight_kg": 62.5,
            "bp": "120/80",
            "doctor_name": "Dr. Mehta",
            "consultation_fee": 500,
            "consultation_payment_mode": "cash",
        },
    )
    assert create_visit.status_code == 201
    assert create_visit.json()["uhid"].startswith("UH")
    assert create_visit.json()["village_town"] == "Narsampet"
    assert create_visit.json()["bp"] == "120/80"
    assert create_visit.json()["consultation_fee"] == 500
    visit_id = create_visit.json()["id"]

    invalid_transition = client.patch(
        f"/api/v1/op-visits/{visit_id}/status",
        headers=headers,
        json={"status": "completed"},
    )
    assert invalid_transition.status_code == 400

    valid_transition = client.patch(
        f"/api/v1/op-visits/{visit_id}/status",
        headers=headers,
        json={"status": "in_consultation"},
    )
    assert valid_transition.status_code == 200
    assert valid_transition.json()["status"] == "in_consultation"

    create_consultation = client.post(
        f"/api/v1/op-visits/{visit_id}/consultation",
        headers=headers,
        json={
            "chief_complaint": "Fever since 2 days",
            "vitals": "BP 120/80, Pulse 80",
            "diagnosis": "Viral fever",
            "clinical_notes": "Hydration advised",
            "advice": "Paracetamol SOS",
            "prescription_medicines": "Paracetamol 650",
            "prescription_dosage": "1-0-1 after food",
            "prescription_duration": "3 days",
        },
    )
    assert create_consultation.status_code == 201
    assert create_consultation.json()["chief_complaint"] == "Fever since 2 days"
    assert create_consultation.json()["prescription_medicines"] == "Paracetamol 650"

    duplicate_consultation = client.post(
        f"/api/v1/op-visits/{visit_id}/consultation",
        headers=headers,
        json={"chief_complaint": "Duplicate"},
    )
    assert duplicate_consultation.status_code == 409

    get_consultation = client.get(f"/api/v1/op-visits/{visit_id}/consultation", headers=headers)
    assert get_consultation.status_code == 200
    assert get_consultation.json()["diagnosis"] == "Viral fever"

    update_consultation = client.patch(
        f"/api/v1/op-visits/{visit_id}/consultation",
        headers=headers,
        json={
            "diagnosis": "Acute viral fever",
            "advice": "Rest and fluids",
            "prescription_notes": "Continue hydration",
        },
    )
    assert update_consultation.status_code == 200
    assert update_consultation.json()["diagnosis"] == "Acute viral fever"
    assert update_consultation.json()["prescription_notes"] == "Continue hydration"

    ready_for_medical = client.patch(
        f"/api/v1/op-visits/{visit_id}/status",
        headers=headers,
        json={"status": "prescription_ready"},
    )
    assert ready_for_medical.status_code == 200
    assert ready_for_medical.json()["status"] == "prescription_ready"

    consultation_pdf = client.get(f"/api/v1/op-visits/{visit_id}/consultation.pdf", headers=headers)
    assert consultation_pdf.status_code == 200
    assert consultation_pdf.headers["content-type"].startswith("application/pdf")
    assert consultation_pdf.content.startswith(b"%PDF")

    create_expense = client.post(
        "/api/v1/expenses",
        headers=headers,
        json={"category": "supplies", "amount": 1250.5, "notes": "Gloves"},
    )
    assert create_expense.status_code == 201
    expense_id = create_expense.json()["id"]

    update_expense = client.patch(
        f"/api/v1/expenses/{expense_id}",
        headers=headers,
        json={"amount": 1500.0},
    )
    assert update_expense.status_code == 200
    assert update_expense.json()["amount"] == 1500.0

    summary = client.get("/api/v1/expenses/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_amount"] >= 1500.0

    create_bill = client.post(
        "/api/v1/medical-bills",
        headers=headers,
        json={
            "patient_id": create_visit.json()["patient_id"],
            "op_visit_id": visit_id,
            "lab_fee": 300,
            "medicine_fee": 200,
            "discount": 100,
            "tax": 0,
            "payment_mode": "cash",
            "status": "unpaid",
        },
    )
    assert create_bill.status_code == 201
    bill_id = create_bill.json()["id"]
    assert create_bill.json()["invoice_no"].startswith("INV-")
    assert create_bill.json()["net_amount"] == 400.0
    assert create_bill.json()["status"] == "unpaid"

    zero_bill = client.post(
        "/api/v1/medical-bills",
        headers=headers,
        json={
            "patient_id": create_visit.json()["patient_id"],
            "op_visit_id": visit_id,
            "lab_fee": 0,
            "medicine_fee": 0,
            "discount": 0,
            "tax": 0,
            "payment_mode": "cash",
            "status": "paid",
        },
    )
    assert zero_bill.status_code == 400
    assert "greater than zero" in zero_bill.json()["detail"]

    invalid_refund = client.patch(
        f"/api/v1/medical-bills/{bill_id}",
        headers=headers,
        json={"status": "refunded", "payment_mode": "upi", "refund_reason": "Duplicate payment"},
    )
    assert invalid_refund.status_code == 400

    mark_paid = client.patch(
        f"/api/v1/medical-bills/{bill_id}",
        headers=headers,
        json={"status": "paid", "payment_mode": "upi"},
    )
    assert mark_paid.status_code == 200
    assert mark_paid.json()["status"] == "paid"
    assert mark_paid.json()["paid_at"] is not None

    update_bill = client.patch(
        f"/api/v1/medical-bills/{bill_id}",
        headers=headers,
        json={"status": "refunded", "payment_mode": "upi", "refund_reason": "Duplicate payment"},
    )
    assert update_bill.status_code == 200
    assert update_bill.json()["status"] == "refunded"
    assert update_bill.json()["refund_reason"] == "Duplicate payment"
    assert update_bill.json()["refunded_at"] is not None

    invoice_pdf = client.get(f"/api/v1/medical-bills/{bill_id}/invoice.pdf", headers=headers)
    assert invoice_pdf.status_code == 200
    assert invoice_pdf.headers["content-type"].startswith("application/pdf")
    assert invoice_pdf.content.startswith(b"%PDF")

    list_bills = client.get("/api/v1/medical-bills", headers=headers)
    assert list_bills.status_code == 200
    assert len(list_bills.json()) == 1

    create_lab_visit = client.post(
        "/api/v1/op-visits",
        headers=headers,
        json={
            "patient_name": "Baby Kiran",
            "village_town": "Warangal",
            "age": 5,
            "weight_kg": 18.4,
            "bp": "100/70",
            "doctor_name": "Dr. Mehta",
            "consultation_fee": 300,
            "consultation_payment_mode": "upi",
        },
    )
    assert create_lab_visit.status_code == 201
    lab_visit_id = create_lab_visit.json()["id"]

    start_lab_visit = client.patch(
        f"/api/v1/op-visits/{lab_visit_id}/status",
        headers=headers,
        json={"status": "in_consultation"},
    )
    assert start_lab_visit.status_code == 200

    save_lab_consultation = client.post(
        f"/api/v1/op-visits/{lab_visit_id}/consultation",
        headers=headers,
        json={"chief_complaint": "Fever"},
    )
    assert save_lab_consultation.status_code == 201

    create_lab = client.post(
        "/api/v1/lab-orders",
        headers=lab_headers,
        json={
            "op_visit_id": lab_visit_id,
            "test_codes": ["CBC", "HB"],
            "custom_test_name": "TORCH Panel",
            "payment_amount": 450,
            "payment_status": "paid",
            "payment_mode": "cash",
        },
    )
    assert create_lab.status_code == 201
    created_labs = create_lab.json()
    assert len(created_labs) == 1
    lab_id = created_labs[0]["id"]
    assert created_labs[0]["status"] == "ordered"
    assert created_labs[0]["payment_status"] == "paid"
    assert created_labs[0]["payment_amount"] == 450.0
    assert len(created_labs[0]["items"]) == 3
    assert created_labs[0]["items"][0]["test_code"] == "CBC"
    assert created_labs[0]["items"][0]["department"] == "common"
    assert created_labs[0]["items"][2]["department"] == "custom"
    assert created_labs[0]["items"][2]["test_name"] == "TORCH Panel"

    catalog = client.get("/api/v1/lab-orders/catalog", headers=headers)
    assert catalog.status_code == 200
    assert any(item["code"] == "CBC" for item in catalog.json())

    forbidden_doctor_lab = client.post(
        "/api/v1/lab-orders",
        headers={"Authorization": f"Bearer {_login('doctor_mehta', 'doctor1234')}"},
        json={"op_visit_id": lab_visit_id, "test_codes": ["CBC"]},
    )
    assert forbidden_doctor_lab.status_code == 403

    list_lab = client.get("/api/v1/lab-orders", headers=headers)
    assert list_lab.status_code == 200
    assert len(list_lab.json()) >= 1

    filtered_lab = client.get(f"/api/v1/lab-orders?op_visit_id={lab_visit_id}", headers=headers)
    assert filtered_lab.status_code == 200
    assert len(filtered_lab.json()) == 1

    update_lab = client.patch(
        f"/api/v1/lab-orders/{lab_id}",
        headers=lab_headers,
        json={"status": "collected"},
    )
    assert update_lab.status_code == 200
    assert update_lab.json()["status"] == "collected"

    progress_lab = client.patch(
        f"/api/v1/lab-orders/{lab_id}",
        headers=lab_headers,
        json={"status": "processing"},
    )
    assert progress_lab.status_code == 200
    complete_lab = client.patch(
        f"/api/v1/lab-orders/{lab_id}",
        headers=lab_headers,
        json={"status": "completed", "result_summary": "All values stable"},
    )
    assert complete_lab.status_code == 200
    assert complete_lab.json()["status"] == "completed"
