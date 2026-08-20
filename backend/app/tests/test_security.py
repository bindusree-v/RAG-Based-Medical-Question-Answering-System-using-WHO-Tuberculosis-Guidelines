"""
MediRAG AI – Security Tests
Tests JWT handling, RBAC, and input validation.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.utils.security import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MySecurePassword!")
        assert hashed != "MySecurePassword!"

    def test_verify_correct_password(self):
        hashed = hash_password("CorrectHorse!")
        assert verify_password("CorrectHorse!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("CorrectHorse!")
        assert verify_password("WrongHorse!", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # bcrypt uses random salt


class TestJWTTokens:
    def test_create_and_decode_token(self):
        data = {"sub": "testuser", "user_id": "abc123", "role": "physician"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded.username == "testuser"
        assert decoded.user_id == "abc123"
        assert decoded.role == "physician"

    def test_invalid_token_returns_none(self):
        result = decode_access_token("this.is.not.a.valid.token")
        assert result is None

    def test_tampered_token_returns_none(self):
        data = {"sub": "user1", "user_id": "u1", "role": "viewer"}
        token = create_access_token(data)
        # Tamper with the payload
        parts = token.split(".")
        tampered = parts[0] + ".tampered" + parts[2]
        result = decode_access_token(tampered)
        assert result is None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def auth_client():
    """Client with a registered + logged-in physician user."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "security_test_doc",
                "email": "security@test.com",
                "password": "SecurePass123!",
                "role": "physician",
            },
        )
        # Login
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "security_test_doc", "password": "SecurePass123!"},
        )
        token = resp.json().get("access_token", "")
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


@pytest.mark.anyio
async def test_protected_endpoint_without_token():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/documents/documents")
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_protected_endpoint_with_invalid_token():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/documents/documents",
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        assert resp.status_code == 401


@pytest.mark.anyio
async def test_authenticated_user_can_list_documents(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/documents/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert "total" in data


@pytest.mark.anyio
async def test_viewer_cannot_delete_documents(auth_client: AsyncClient):
    """Viewer role should be blocked from delete (requires admin/physician)."""
    # Register viewer
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "viewer_test_user",
                "email": "viewer@test.com",
                "password": "ViewerPass123!",
                "role": "viewer",
            },
        )
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": "viewer_test_user", "password": "ViewerPass123!"},
        )
        viewer_token = login.json().get("access_token", "")
        # Attempt delete with viewer token
        resp = await client.delete(
            "/api/v1/documents/document/nonexistent-id",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        # Should be 403 Forbidden (not 404, since RBAC check comes first)
        assert resp.status_code == 403


@pytest.mark.anyio
async def test_query_validation_rejects_too_short(auth_client: AsyncClient):
    """Medical query must be at least 3 characters."""
    resp = await auth_client.post(
        "/api/v1/query/medical-query",
        json={"query": "ab"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_drug_interaction_requires_both_drugs(auth_client: AsyncClient):
    """Drug interaction endpoint requires drug_a and drug_b."""
    resp = await auth_client.post(
        "/api/v1/query/drug-interaction",
        json={"drug_a": "", "drug_b": "aspirin"},
    )
    assert resp.status_code == 422
