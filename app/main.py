from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import auth, users, ai, image_generation, analysis, diagram, seo
from app.database import engine, Base
# Import all models to ensure tables are created
from app.models import users as user_models, ai as ai_models, logs as log_models

# Create tables logic
Base.metadata.create_all(bind=engine)

# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
from app.services.background_tasks import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
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

# ── Auto-Healing Runtime Exception Hook ──────────────────────────────────────
# Defers unhandled exceptions to the L4/L5 Autonomous Intelligence System
import traceback
import logging

logger = logging.getLogger(__name__)

@app.middleware("http")
async def auto_heal_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"RUNTIME_ERROR: {str(e)}\n{error_details}")
        
        # Trigger Autonomous Healing System asynchronously
        from app.zara_ai.core.orchestrator import autonomous_loop
        import asyncio
        asyncio.create_task(autonomous_loop(str(e), error_details))
        
        # We don't bubble 500 directly, instead we tell the client we're working on it
        return JSONResponse(
            status_code=500, 
            content={"detail": "Zara AI encountered an error and is autonomously verifying a patch."}
        )

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
