class SecurityHeadersMiddleware:
    """Middleware to inject hardened security headers into all HTTP responses."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Inject security headers if not already present
                security_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
                ]
                for header_name, header_value in security_headers:
                    if not any(h[0].lower() == header_name for h in headers):
                        headers.append((header_name, header_value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


"""Authentication utilities supporting bcrypt/Argon2 password hashing and JWT token management."""

import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Security, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.tenant import Tenant

# Setup password hashing context supporting bcrypt and argon2
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-insecure-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/tenants/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password (supports both Argon2 and bcrypt)."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using the preferred secure scheme (Argon2 by default)."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token containing claims."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token, raising HTTP exceptions on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Verify admin API key."""
    admin_key = os.getenv("ADMIN_API_KEY", "dev-admin-secure-api-key-replace-in-prod")
    if not api_key or api_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing administrative API Key",
        )
    return api_key


def get_current_active_tenant(
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Tenant:
    """Verify either an active Tenant API Key or a valid Tenant JWT Token for fine queries/operations."""
    tenant = None

    # 1. Check API Key authentication
    if api_key:
        api_key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        tenant = db.query(Tenant).filter(Tenant.api_key_hash == api_key_hash).first()

    # 2. Check JWT Token authentication if API key not provided or not found
    elif token:
        payload = decode_access_token(token)
        tenant_id = payload.get("sub")
        if tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key or JWT Token credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive or subscription license has expired",
        )

    return tenant
