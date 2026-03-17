from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
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


def test_report_endpoints() -> None:
    token = _bootstrap_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    create_visit = client.post(
        "/api/v1/op-visits",
        headers=headers,
        json={
            "patient_name": "Ravi",
            "village_town": "Hanamkonda",
            "age": 44,
            "weight_kg": 70.0,
            "bp": "130/85",
            "doctor_name": "Dr. Mehta",
            "consultation_fee": 600,
            "consultation_payment_mode": "cash",
        },
    )
    assert create_visit.status_code == 201

    create_expense = client.post(
        "/api/v1/expenses",
        headers=headers,
        json={"category": "supplies", "amount": 1000, "notes": "kits"},
    )
    assert create_expense.status_code == 201

    start_visit = client.patch(
        f"/api/v1/op-visits/{create_visit.json()['id']}/status",
        headers=headers,
        json={"status": "in_consultation"},
    )
    assert start_visit.status_code == 200

    consultation = client.post(
        f"/api/v1/op-visits/{create_visit.json()['id']}/consultation",
        headers=headers,
        json={"chief_complaint": "Routine checkup"},
    )
    assert consultation.status_code == 201

    ready_for_medical = client.patch(
        f"/api/v1/op-visits/{create_visit.json()['id']}/status",
        headers=headers,
        json={"status": "prescription_ready"},
    )
    assert ready_for_medical.status_code == 200

    create_bill = client.post(
        "/api/v1/medical-bills",
        headers=headers,
        json={
            "patient_id": create_visit.json()["patient_id"],
            "op_visit_id": create_visit.json()["id"],
            "lab_fee": 200,
            "medicine_fee": 100,
            "discount": 50,
            "tax": 0,
            "payment_mode": "cash",
            "status": "paid",
        },
    )
    assert create_bill.status_code == 201

    daily_summary = client.get("/api/v1/reports/daily-summary", headers=headers)
    assert daily_summary.status_code == 200
    assert daily_summary.json()["op_count"] >= 1
    assert daily_summary.json()["revenue"] >= 850
    assert daily_summary.json()["expenses"] >= 1000

    op_summary = client.get("/api/v1/reports/op-summary", headers=headers)
    assert op_summary.status_code == 200
    assert op_summary.json()["total"] >= 1

    revenue_trend = client.get("/api/v1/reports/revenue-trend?days=7", headers=headers)
    assert revenue_trend.status_code == 200
    assert len(revenue_trend.json()) == 7

    expense_trend = client.get("/api/v1/reports/expense-trend?days=7", headers=headers)
    assert expense_trend.status_code == 200
    assert len(expense_trend.json()) == 7

    daily_csv = client.get("/api/v1/reports/daily-summary.csv", headers=headers)
    assert daily_csv.status_code == 200
    assert daily_csv.headers["content-type"].startswith("text/csv")
    assert "op_count" in daily_csv.text

    op_csv = client.get("/api/v1/reports/op-visits.csv", headers=headers)
    assert op_csv.status_code == 200
    assert op_csv.headers["content-type"].startswith("text/csv")
    assert "uhid" in op_csv.text
    assert "village_town" in op_csv.text
    assert "patient_name" in op_csv.text

    bills_csv = client.get("/api/v1/reports/medical-bills.csv", headers=headers)
    assert bills_csv.status_code == 200
    assert bills_csv.headers["content-type"].startswith("text/csv")
    assert "net_amount" in bills_csv.text

    expenses_csv = client.get("/api/v1/reports/expenses.csv", headers=headers)
    assert expenses_csv.status_code == 200
    assert expenses_csv.headers["content-type"].startswith("text/csv")
    assert "category" in expenses_csv.text

    range_summary = client.get(
        "/api/v1/reports/date-range-summary?start_date=2024-01-01&end_date=2100-01-01",
        headers=headers,
    )
    assert range_summary.status_code == 400

    today = daily_summary.json()["date"]
    range_summary_ok = client.get(
        f"/api/v1/reports/date-range-summary?start_date={today}&end_date={today}",
        headers=headers,
    )
    assert range_summary_ok.status_code == 200
    assert range_summary_ok.json()["op_count"] >= 1

    doctor_summary = client.get(
        f"/api/v1/reports/doctor-op-summary?start_date={today}&end_date={today}",
        headers=headers,
    )
    assert doctor_summary.status_code == 200
    assert isinstance(doctor_summary.json(), list)
    assert len(doctor_summary.json()) >= 1
    assert doctor_summary.json()[0]["doctor_name"] == "Dr. Mehta"

    expense_by_category = client.get(
        f"/api/v1/reports/expense-category-summary?start_date={today}&end_date={today}",
        headers=headers,
    )
    assert expense_by_category.status_code == 200
    assert isinstance(expense_by_category.json(), list)
    assert len(expense_by_category.json()) >= 1
    assert expense_by_category.json()[0]["category"] == "supplies"

    daily_pdf = client.get("/api/v1/reports/daily-summary.pdf", headers=headers)
    assert daily_pdf.status_code == 200
    assert daily_pdf.headers["content-type"].startswith("application/pdf")
    assert daily_pdf.content.startswith(b"%PDF")
