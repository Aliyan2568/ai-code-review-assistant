"""Health-check endpoint: confirms the API is up and the database is reachable."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database import check_db_connection
from app.schemas.health import HealthResponse
from app.utils.logger import get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
def health_check():
    try:
        check_db_connection()
        return HealthResponse(status="ok", database="connected")
    except SQLAlchemyError as exc:
        logger.error("Database health check failed: %s", exc)
        body = HealthResponse(status="degraded", database="unavailable")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body.model_dump())
