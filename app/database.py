import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configure engine based on database URL
db_url = settings.DATABASE_URL

# If relative SQLite path, resolve to absolute path in project root
if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////") and ":memory:" not in db_url:
    rel_path = db_url[len("sqlite:///"):]
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    abs_db_path = os.path.join(BASE_DIR, rel_path).replace("\\", "/")
    db_url = f"sqlite:///{abs_db_path}"

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for background jobs and tasks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables idempotently without dropping data."""
    # Import all models so that Base.metadata has all table definitions
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
