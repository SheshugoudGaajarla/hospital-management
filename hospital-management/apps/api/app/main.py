import json
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.laboratory import router as laboratory_router
from app.api.v1.operations import router as operations_router
from app.api.v1.reports import router as reports_router
from app.core.config import settings
from app.core.metrics import metrics_store
from app.core.rate_limit import get_client_ip

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("hospital.api")

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(operations_router)
app.include_router(laboratory_router)
app.include_router(reports_router)


@app.middleware("http")
async def request_context_logging(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started_at = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        duration_seconds = duration_ms / 1000
        route = request.scope.get("route")
        route_path = request.url.path
        if route is not None and getattr(route, "path", None):
            route_path = str(route.path)
        metrics_store.record_http(
            method=request.method,
            path=route_path,
            status_code=response.status_code if response else 500,
            duration_seconds=duration_seconds,
        )
        if settings.request_log_enabled:
            payload = {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query,
                "status_code": response.status_code if response else 500,
                "duration_ms": duration_ms,
                "client_ip": get_client_ip(request),
            }
            logger.info(json.dumps(payload, separators=(",", ":")))
        if response is not None:
            response.headers["X-Request-ID"] = request_id


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "env": settings.app_env}
