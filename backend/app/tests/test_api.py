"""
MediRAG AI – API Integration Tests
Uses FastAPI TestClient with an in-memory SQLite database.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_root(client: AsyncClient):
    """Root endpoint returns app info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "MediRAG" in data["name"]
    assert "disclaimer" in data


@pytest.mark.anyio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint returns component statuses."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "version" in data


@pytest.mark.anyio
async def test_login_invalid_credentials(client: AsyncClient):
    """Login with wrong credentials returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "notauser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_endpoint_requires_auth(client: AsyncClient):
    """Documents endpoint requires authentication."""
    response = await client.get("/api/v1/documents")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_register_and_login(client: AsyncClient):
    """Register a new user, then login successfully."""
    # Register
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testphysician",
            "email": "doc@hospital.com",
            "password": "SecurePass123!",
            "role": "physician",
        },
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["username"] == "testphysician"
    assert user_data["role"] == "physician"

    # Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "testphysician", "password": "SecurePass123!"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_duplicate_registration_fails(client: AsyncClient):
    """Registering the same username twice returns 409."""
    payload = {
        "username": "unique_doc_test",
        "email": "unique@test.com",
        "password": "TestPass123!",
        "role": "viewer",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.anyio
async def test_validate_document_endpoint(client: AsyncClient):
    """Validate endpoint correctly classifies medical content."""
    # Register + login
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "validator_user",
            "email": "validator@test.com",
            "password": "ValidPass123!",
            "role": "researcher",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "validator_user", "password": "ValidPass123!"},
    )
    token = login.json()["access_token"]

    medical_text = b"""
    This randomized controlled trial evaluated the efficacy of atorvastatin 40mg
    in patients with hypercholesterolemia. Methods: 500 patients were enrolled.
    Primary endpoint: LDL reduction at 12 weeks. Results: Mean LDL reduction was
    48% (p<0.001). Adverse events: myalgia in 3% of patients. Dosage adjustments
    were made based on liver function tests. Contraindications include active liver
    disease. Clinical guidelines recommend statin therapy for cardiovascular prevention.
    """

    resp = await client.post(
        "/api/v1/documents/validate-document",
        files={"file": ("cardiology_trial.pdf", medical_text, "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["is_valid"] is True
