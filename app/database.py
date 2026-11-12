"""Database engine, session factory, and the FastAPI session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class that all SQLAlchemy models inherit from."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for one request, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create any missing tables. Existing tables are left untouched."""
    import app.models  # noqa: F401  (registers the models on Base.metadata)

    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Return True if the database answers a simple query."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
