from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.metrics import metrics_store

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Health check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", summary="Prometheus metrics", response_class=PlainTextResponse)
def metrics() -> PlainTextResponse:
    return PlainTextResponse(content=metrics_store.render_prometheus(), media_type="text/plain")
