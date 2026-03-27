from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, users, ai, image_generation, analysis, diagram, seo
from app.database import engine, Base
# Import all models to ensure tables are created
from app.models import users as user_models, ai as ai_models, logs as log_models

# Create tables logic
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Start Background Tasks (Auto-Delete)
from app.services.background_tasks import start_scheduler
@app.on_event("startup")
def startup_event():
    start_scheduler()

# CORS configuration - Highly permissive for debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
