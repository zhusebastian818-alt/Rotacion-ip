"""Service layer for managing tenants, API keys, and enterprise registration."""

import secrets
import hashlib
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.tenant import Tenant
from app.models.tenant_schema import TenantCreateRequest, TenantResponse, TenantLoginRequest
from app.core.security import get_password_hash, verify_password, create_access_token

logger = logging.getLogger(__name__)


class TenantService:
    """Service handling tenant creation, authentication, and cryptographic API key generation."""

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key securely for storage."""
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    def register_tenant(self, db: Session, payload: TenantCreateRequest) -> TenantResponse:
        """Register a new tenant, generate a secure API key, and persist to database."""
        # Check if tenant ID or email already exists
        existing_tenant = db.query(Tenant).filter(
            (Tenant.id == payload.id) | (Tenant.email == payload.email)
        ).first()

        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant with this ID or email already exists."
            )

        # Generate secure random API key
        raw_api_key = f"sk_live_{secrets.token_hex(24)}"
        api_hash = self.hash_api_key(raw_api_key)

        # Hash password if provided
        pwd_hash = get_password_hash(payload.password) if payload.password else get_password_hash(secrets.token_hex(16))

        tenant = Tenant(
            id=payload.id,
            name=payload.name,
            email=payload.email,
            password_hash=pwd_hash,
            api_key_hash=api_hash,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        logger.info("Successfully registered new tenant: %s (%s)", tenant.id, tenant.name)

        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            email=tenant.email,
            is_active=tenant.is_active,
            api_key=raw_api_key,
            created_at=tenant.created_at,
        )

    def authenticate_tenant(self, db: Session, payload: TenantLoginRequest) -> str:
        """Authenticate tenant email and password, returning a JWT access token."""
        tenant = db.query(Tenant).filter(Tenant.email == payload.email).first()
        if not tenant or not tenant.password_hash or not verify_password(payload.password, tenant.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is inactive or license revoked."
            )

        access_token = create_access_token(data={"sub": tenant.id, "email": tenant.email})
        return access_token
