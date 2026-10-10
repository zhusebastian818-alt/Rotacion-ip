"""FastAPI endpoints for tenant registration and B2B subscription management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_api_key
from app.models.tenant_schema import TenantCreateRequest, TenantResponse, TenantLoginRequest, TokenResponse
from app.services.tenant_service import TenantService

router = APIRouter(
    prefix="/tenants",
    tags=["Tenant Management"],
)

tenant_service = TenantService()


@router.post(
    "/register",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Tenant Company",
    description="Registers a new B2B subscriber/company, creates an isolated tenant entity, and returns a secure API key.",
)
async def register_tenant(
    payload: TenantCreateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Register tenant endpoint protected by administrative API key and strict Pydantic validation."""
    return tenant_service.register_tenant(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Tenant Login (OAuth2 / JWT)",
    description="Authenticates a tenant via email and password, returning a JWT access token for portal/API access.",
)
async def login_tenant(
    payload: TenantLoginRequest,
    db: Session = Depends(get_db),
):
    """Tenant authentication endpoint returning a secure JWT token."""
    token = tenant_service.authenticate_tenant(db, payload)
    return TokenResponse(access_token=token, token_type="bearer")
