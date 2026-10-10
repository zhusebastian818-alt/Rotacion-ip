"""V1 API Router aggregator."""

from fastapi import APIRouter
from app.api.v1.endpoints import health, fines, tenants

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router)
api_router.include_router(fines.router)
api_router.include_router(tenants.router)
