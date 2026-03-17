# Hospital Management

Monorepo for hospital management MVP with long-term scalable structure.

## Phase 1 Status
- Project bootstrap completed
- Frontend skeleton (Next.js) completed
- Backend skeleton (FastAPI) completed
- Alembic migration baseline added
- Docker Compose local stack added
- Basic CI smoke checks added

## Backend Tooling (Industry Ready Baseline)
- Python package/dependency manager: `uv`
- Backend config source: `apps/api/pyproject.toml`
- Quality gates in CI: `ruff`, `mypy`, `pytest`

## Phase 2 (Auth + RBAC) API Endpoints
- `POST /api/v1/auth/bootstrap-admin` (one-time first user creation)
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me` (bearer token required)
- `GET /api/v1/auth/admin-only` (admin role required)

## Phase 2 Frontend (Auth UI)
- `/login`: username/password sign-in
- `/dashboard`: protected landing page
- `/op`, `/medical-bill`, `/expenses`: protected pages with role guards
- Uses `NEXT_PUBLIC_API_BASE_URL` from `apps/web/.env.example`

## Phase 3 (CRUD Modules)
- Run new migration:
  - `DATABASE_URL=\"postgresql+psycopg://postgres:postgres@localhost:5432/hospital_dev\" uv run alembic upgrade head`
- Backend endpoints:
  - `POST/GET /api/v1/op-visits`
  - `PATCH /api/v1/op-visits/{visit_id}/status`
  - `POST/GET /api/v1/expenses`
  - `PATCH /api/v1/expenses/{expense_id}`
  - `GET /api/v1/expenses/summary`
  - `POST/GET /api/v1/medical-bills`
  - `PATCH /api/v1/medical-bills/{bill_id}`

## Phase 4 (Hardening)
- Added request validation (phone digits, non-negative bill math, positive expense amounts)
- Added OP status transition rules (`waiting -> in_consultation -> completed/cancelled`)
- Added audit logs table and event writes for create/update operations
- Added endpoint tests:
  - `tests/test_auth.py`
  - `tests/test_operations.py`

## Phase 5 (Reporting)
- New reporting endpoints:
  - `GET /api/v1/reports/daily-summary?date=YYYY-MM-DD`
  - `GET /api/v1/reports/op-summary?date=YYYY-MM-DD`
  - `GET /api/v1/reports/revenue-trend?days=7`
  - `GET /api/v1/reports/expense-trend?days=7`
- Dashboard now pulls live KPIs and queue summary from report APIs.
- Added report tests:
  - `tests/test_reports.py`

## Phase 5.2 (Advanced Reporting)
- Added advanced analytics endpoints:
  - `GET /api/v1/reports/date-range-summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
  - `GET /api/v1/reports/doctor-op-summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
  - `GET /api/v1/reports/expense-category-summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- Added PDF export endpoint:
  - `GET /api/v1/reports/daily-summary.pdf?date=YYYY-MM-DD`
- Updated report UI page:
  - `/reports/daily-print` now supports PDF download and range analytics panels.

## Phase 5.3 (Billing Hardening)
- Added medical bill invoice fields and lifecycle columns:
  - `invoice_no`, `paid_at`, `refunded_at`, `refund_reason`
- Added strict bill transition flow:
  - `unpaid -> paid -> refunded`
- Added invoice PDF endpoint:
  - `GET /api/v1/medical-bills/{bill_id}/invoice.pdf`
- Updated billing UI:
  - `/medical-bill` now supports initial bill status, `Mark Paid`, `Refund`, and invoice PDF download.

## Phase 6 (Security Hardening)
- Added API request-level rate limiting (IP based):
  - Auth endpoints (`bootstrap-admin`, `login`)
  - Write endpoints (`op-visits`, `expenses`, `medical-bills` create/update)
- Added request observability middleware:
  - `X-Request-ID` response header
  - Structured request logs (method, path, status, duration, client IP)
- Hardened CORS handling:
  - Uses parsed `CORS_ORIGINS` list
  - Restricts methods to `GET, POST, PATCH, OPTIONS`
  - Restricts headers to `Authorization, Content-Type, X-Request-ID`
- Added new env knobs:
  - `LOG_LEVEL`, `REQUEST_LOG_ENABLED`
  - `RATE_LIMIT_ENABLED`, `RATE_LIMIT_LOGIN_PER_MINUTE`
  - `RATE_LIMIT_WRITE_PER_MINUTE`, `RATE_LIMIT_BOOTSTRAP_PER_HOUR`

## Phase 6.1 (Observability)
- Added Prometheus-compatible metrics endpoint:
  - `GET /health/metrics`
- Added core API metrics:
  - request count, 5xx count, latency histogram
  - auth failure and auth rate-limit counters
- Added observability stack files:
  - `infra/observability/docker-compose.observability.yml`
  - `infra/observability/prometheus/prometheus.yml`
  - `infra/observability/prometheus/alert_rules.yml`
  - `infra/observability/grafana/...` provisioning and dashboard

### Run Observability Stack (Docker)
- Start app stack:
  - `docker compose -f infra/docker/docker-compose.yml up -d --build`
- Start monitoring stack:
  - `docker compose -f infra/docker/docker-compose.yml -f infra/observability/docker-compose.observability.yml up -d prometheus grafana`
- Access:
  - Prometheus: `http://localhost:9090`
  - Grafana: `http://localhost:3001` (`admin` / `admin`)

## Phase 6.2 (Backup and Recovery)
- Added automated backup service (`db-backup`) in Docker compose.
- Added manual backup and restore scripts:
  - `scripts/db-backup.sh`
  - `scripts/db-restore.sh`
- Added backup execution scripts used by backup container:
  - `scripts/db-backup-once.sh`
  - `scripts/db-backup-loop.sh`
- Added runbook:
  - `docs/runbooks/backup-recovery.md`

### Backup Commands
- Manual backup:
  - `./scripts/db-backup.sh`
- Restore (interactive confirmation):
  - `./scripts/db-restore.sh backups/postgres/<backup-file>.sql.gz`
- Restore (non-interactive):
  - `./scripts/db-restore.sh backups/postgres/<backup-file>.sql.gz --yes`

## Phase 8.1 (Clinical Consultation)
- Added consultations schema and migration:
  - `consultations` table linked 1:1 to `op_visits`
  - fields: chief complaint, vitals, diagnosis, notes, advice, follow-up date
- Added consultation APIs:
  - `GET /api/v1/op-visits/{visit_id}/consultation`
  - `POST /api/v1/op-visits/{visit_id}/consultation`
  - `PATCH /api/v1/op-visits/{visit_id}/consultation`
- Updated OP UI:
  - `Consult` action on OP queue rows
  - consultation form panel with save/update flow

## Phase 8.2 (OP Workflow UX Upgrade)
- Improved OP queue usability:
  - status counters (`waiting`, `in consultation`, `completed`, `cancelled`)
  - queue filters (status dropdown + search by patient/token/phone/doctor)
  - clearer action buttons on each row
- Improved consultation experience:
  - explicit read-only notes mode for completed/cancelled visits
  - visit status and last-updated timestamp in consultation panel
  - clearer empty-state guidance for consultation actions

## Phase 8.3 (Prescription + Consultation Print)
- Added prescription fields to consultation:
  - `prescription_medicines`, `prescription_dosage`, `prescription_duration`, `prescription_notes`
  - migration: `0007_add_consult_rx_fields`
- Added consultation printable PDF endpoint:
  - `GET /api/v1/op-visits/{visit_id}/consultation.pdf`
- Updated OP UI:
  - consultation form includes prescription sections
  - `Print Prescription` action to download consultation sheet PDF

## Phase A + B (Role Redesign + OP Intake Refactor)
- Role model updated to:
  - `doctor` (super user access)
  - `admin` (finance + operations)
  - `laboratory` (reports and lab analytics access)
  - `medical` (billing and pharmacy scope)
  - `operations` (front desk / OP scope)
- Added migration:
  - `0008_roles_op_vitals`
  - maps old roles (`reception -> operations`, `billing -> medical`)
  - makes `patients.phone` nullable
  - adds OP vitals columns: `age`, `weight_kg`, `bp`
- OP intake contract changed:
  - request now captures `uhid`, `patient_name`, `age`, `weight_kg`, `bp`, `doctor_name`
  - OP response now returns `uhid`, `age`, `weight_kg`, `bp`
- Role-based route guards and frontend page guards updated for new role names and purview.

## Phase B.1 (Village/Town in OP)
- Added required patient location field:
  - `village_town` in `patients` table
  - migration: `0009_add_patient_village_town`
- OP intake now captures `village_town` and doctor queue displays it.
- OP export CSV now includes `village_town`.

## Phase L1 (Laboratory Module - Separate from Medical)
- Added dedicated lab orders domain:
  - table: `lab_orders`
  - migration: `0010_create_lab_orders`
- Added Laboratory APIs:
  - `POST /api/v1/lab-orders` (doctor/admin)
  - `GET /api/v1/lab-orders` (lab/admin/doctor; doctor sees own patients)
  - `PATCH /api/v1/lab-orders/{order_id}` (lab/admin)
- Added dedicated frontend page:
  - `/laboratory` with lab order creation and status workflow
- Updated role routing:
  - laboratory users now land on `/laboratory` after login
  - separate from `/medical-bill`

## Run API Locally Without Docker
```bash
cd apps/api
uv sync --dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Locally (Docker)
- `./scripts/dev-up.sh`
- API health: `http://localhost:8000/health`
- Web: `http://localhost:3000`

## Structure
- `apps/web`: frontend
- `apps/api`: backend
- `apps/worker`: async worker
- `infra/docker`: local orchestration
- `environments`: env templates
- `docs`: architecture and runbooks
