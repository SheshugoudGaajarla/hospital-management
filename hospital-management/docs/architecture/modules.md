# Module Boundaries

## API Modules (apps/api/app)
- `api/v1`: route definitions
- `core`: settings, security, auth helpers
- `db`: engine/session setup
- `models`: SQLAlchemy models
- `schemas`: pydantic request/response schemas
- `repositories`: DB access layer
- `services`: business logic
- `workers`: producer hooks for async tasks

## Initial Domain Areas
- `auth`
- `patients`
- `appointments`
- `consultations`
- `billing`
- `audit`
