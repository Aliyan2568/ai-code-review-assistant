"""Database engine, session factory, and the FastAPI session dependency."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
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


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return cfg


def run_migrations(bind=None) -> None:
    """Bring the database schema up to date with `alembic upgrade head`.

    A database created before migrations existed (tables present, no
    alembic_version table) is stamped as current instead of re-created.
    """
    from alembic import command

    cfg = _alembic_config()
    with (bind or engine).begin() as conn:
        cfg.attributes["connection"] = conn
        tables = set(inspect(conn).get_table_names())
        if "reviews" in tables and "alembic_version" not in tables:
            command.stamp(cfg, "0001")
        command.upgrade(cfg, "head")


def init_db() -> None:
    """Run database migrations on startup."""
    run_migrations()


def check_db_connection() -> bool:
    """Return True if the database answers a simple query."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
