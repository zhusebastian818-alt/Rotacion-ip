"""Health and liveness probes."""

from datetime import datetime, timezone
from fastapi import APIRouter, status
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(tags=["Health"])


class HealthStatusResponse(BaseModel):
    status: str
    environment: str
    version: str
    timestamp: datetime


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Liveness probe for orchestrators and health monitoring without disclosing system internals.",
)
async def get_health():
    return HealthStatusResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )
