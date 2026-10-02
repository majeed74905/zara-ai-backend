from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


def _normalize_database_url(url: str) -> str:
    """
    Always name the PostgreSQL driver explicitly.

    SQLAlchemy 2.1 switched the default driver for bare `postgresql://` URLs from
    psycopg2 to psycopg (v3). We ship psycopg2-binary, so a bare URL crashed on
    startup with "No module named 'psycopg'". Some providers also hand out the
    legacy `postgres://` scheme, which SQLAlchemy rejects outright.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_database_url(settings.DATABASE_URL)

# Handling SQLite vs Postgres URLs
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 300,
    })

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
