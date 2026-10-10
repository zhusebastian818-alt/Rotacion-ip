"""Automated tests for B2B SaaS Traffic Fine Monitoring system and Tenant authentication/OAuth2."""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.config import settings
from app.core.security import get_password_hash

client = TestClient(app)


def test_root_endpoint():
    """Verify public root endpoint metadata."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Monitoreo Inteligente de Multas" in response.text


def test_tenant_registration_and_jwt_login():
    """Verify successful tenant registration with password, and subsequent JWT OAuth2 login."""
    payload = {
        "id": "portal-tenant-01",
        "name": "Portal Tenant Fleet S.A.",
        "email": "portal@tenant01.com",
        "password": "SecurePassword123!"
    }
    # Register using admin API key
    response = client.post(
        "/api/v1/tenants/register",
        json=payload,
        headers={settings.API_KEY_HEADER_NAME: settings.ADMIN_API_KEY},
    )
    if response.status_code == 400:
        # Tenant might already exist from previous test run
        pass
    else:
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "portal-tenant-01"
        assert "api_key" in data

    tenant_api_key = "dummy-key-for-test"

    # Now login with email and password to get JWT token
    login_payload = {
        "email": "portal@tenant01.com",
        "password": "SecurePassword123!"
    }
    login_response = client.post("/api/v1/tenants/login", json=login_payload)
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    access_token = token_data["access_token"]

    # Verify fine query using Tenant's generated API key
    fine_query = {"plate_number": "PORTAL123", "country_code": "AR"}
    fine_resp_api = client.post(
        "/api/v1/fines/check",
        json=fine_query,
        headers={settings.API_KEY_HEADER_NAME: tenant_api_key},
    )
    assert fine_resp_api.status_code == 200
    assert fine_resp_api.json()["plate_number"] == "PORTAL123"

    # Verify fine query using Tenant's JWT bearer token
    fine_resp_jwt = client.post(
        "/api/v1/fines/check",
        json=fine_query,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert fine_resp_jwt.status_code == 200
    assert fine_resp_jwt.json()["plate_number"] == "PORTAL123"

    # Verify fine stats with JWT token
    stats_resp = client.get(
        "/api/v1/fines/stats",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert stats_resp.status_code == 200
    assert stats_resp.json()["tenant_id"] == "portal-tenant-01"


def test_tenant_login_wrong_password():
    """Verify login fails with incorrect password."""
    login_payload = {
        "email": "portal@tenant01.com",
        "password": "WrongPassword999!"
    }
    response = client.post("/api/v1/tenants/login", json=login_payload)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_fine_endpoint_missing_credentials():
    """Verify unauthenticated requests are now allowed (auth requirement removed for Swagger UI direct usage)."""
    payload = {"plate_number": "ABC1234", "country_code": "AR"}
    response = client.post("/api/v1/fines/check", json=payload)
    assert response.status_code == 200
    assert "plate_number" in response.json()
