"""Pydantic schemas for Tenant registration and management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class TenantCreateRequest(BaseModel):
    """Schema for registering a new tenant/company."""
    id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9_\-]+$",
        description="Unique alphanumeric identifier for the tenant",
        examples=["enterprise-logistics", "fleet-co-ar"]
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Legal company name or organization name"
    )
    email: str = Field(
        ...,
        description="Administrative contact email address"
    )
    password: Optional[str] = Field(
        None,
        min_length=6,
        description="Optional password for tenant portal login"
    )

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Strict regex validation for email to avoid external dependency issues."""
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email address format")
        return v.lower()


class TenantResponse(BaseModel):
    """Schema for tenant registration response (including generated API key for first-time display)."""
    id: str
    name: str
    email: str
    is_active: bool
    api_key: str = Field(..., description="Generated API key for the tenant. Save this securely as it will not be shown again.")
    created_at: datetime

    class Config:
        from_attributes = True


class TenantLoginRequest(BaseModel):
    """Schema for Tenant login request."""
    email: str = Field(..., description="Tenant registered email")
    password: str = Field(..., description="Tenant account password")


class TokenResponse(BaseModel):
    """Schema for OAuth2 JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
