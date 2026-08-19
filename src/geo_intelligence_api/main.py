import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

from .api import router
from .config import get_settings
from .database import get_db
from .logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description="Serviço geoespacial demonstrativo para análise territorial",
)
app.include_router(router, prefix="/api/v1", tags=["geoespacial"])


@app.middleware("http")
async def observability(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:128]
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )
    return response


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "vivo"}


@app.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "pronto", "banco": "disponível"}


@app.get("/map", response_class=HTMLResponse, include_in_schema=False)
def map_page() -> str:
    return (Path(__file__).parent / "static" / "map.html").read_text(encoding="utf-8")


Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, include_in_schema=False)
