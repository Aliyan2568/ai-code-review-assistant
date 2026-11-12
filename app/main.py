"""FastAPI application entry point.

Run with:  uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import init_db
from app.routes import analyze, health, review
from app.utils.logger import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_db()
        logger.info("Database tables are ready")
    except SQLAlchemyError as exc:
        # Keep the API up (e.g. /analyze works without a DB); /health will report the problem.
        logger.error("Could not create database tables: %s", exc)
    logger.info("%s started (environment=%s)", settings.app_name, settings.environment)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Analyzes Python code for bugs, security issues, and inefficiencies "
    "using static analysis and AI.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(review.router)


@app.get("/", tags=["Root"])
def root():
    return {"message": f"{settings.app_name} is running. Visit /docs for the API docs."}
