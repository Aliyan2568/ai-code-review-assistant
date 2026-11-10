"""FastAPI application entry point.

Run with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.config import get_settings
from app.routes import health
from app.utils.logger import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Analyzes Python code for bugs, security issues, and inefficiencies "
    "using static analysis and AI.",
    version="0.1.0",
)

app.include_router(health.router)


@app.get("/", tags=["Root"])
def root():
    return {"message": f"{settings.app_name} is running. Visit /docs for the API docs."}


logger.info("%s started (environment=%s)", settings.app_name, settings.environment)
