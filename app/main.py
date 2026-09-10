from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import auth, users, ai, image_generation, analysis, diagram, seo
from app.database import engine, Base
# Import all models to ensure tables are created
from app.models import users as user_models, ai as ai_models, logs as log_models

# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
from app.services.background_tasks import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    # Shutdown cleanup can go here if needed

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS — allow specific production origins and localhost for development
ALLOWED_ORIGINS = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Unhandled Exception Hook ─────────────────────────────────────────────────
# Logs the full traceback for developers and returns a friendly message to users.
# The experimental autonomous-healing loop (sends tracebacks to an external LLM)
# is OFF unless ZARA_AUTO_HEAL_ENABLED=true is explicitly set.
import os
import traceback
import logging

logger = logging.getLogger(__name__)

AUTO_HEAL_ENABLED = os.getenv("ZARA_AUTO_HEAL_ENABLED", "false").strip().lower() == "true"

@app.middleware("http")
async def unhandled_error_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"RUNTIME_ERROR on {request.method} {request.url.path}: {e}\n{error_details}")

        if AUTO_HEAL_ENABLED:
            from app.zara_ai.core.orchestrator import autonomous_loop
            import asyncio
            asyncio.create_task(autonomous_loop(str(e), error_details))

        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our side. Please try again in a moment."}
        )

import uuid
import time

@app.middleware("http")
async def request_trace_middleware(request, call_next):
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = req_id
    logger.info(f"[{req_id}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
    return response

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["ai"])
app.include_router(image_generation.router, prefix=f"{settings.API_V1_STR}/image-generation", tags=["image-generation"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}/analysis", tags=["analysis"])
app.include_router(diagram.router, prefix=f"{settings.API_V1_STR}/diagram", tags=["diagram"])
app.include_router(seo.router, prefix=f"{settings.API_V1_STR}/seo", tags=["seo"])
from app.api import reports
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])

@app.get("/")
def root():
    return {"message": "Welcome to Zara AI Backend"}


@app.get("/health")
async def health_check():
    db_status = "ok"
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Health check DB ping failed: {e}")
        db_status = "degraded"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "Zara AI Backend",
        "version": "1.0.0",
        "database": db_status
    }
