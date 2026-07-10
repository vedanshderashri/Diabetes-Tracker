"""
MedAI Assistant - Authentication Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    """Test user registration."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@medai.com",
        "password": "securepassword123",
        "full_name": "New User",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@medai.com"
    assert data["user"]["role"] == "patient"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test duplicate email registration."""
    user_data = {
        "email": "duplicate@medai.com",
        "password": "securepassword123",
        "full_name": "First User",
    }
    await client.post("/api/v1/auth/register", json=user_data)
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """Test user login."""
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "logintest@medai.com",
        "password": "securepassword123",
        "full_name": "Login Test",
    })
    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "logintest@medai.com",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpwd@medai.com",
        "password": "securepassword123",
        "full_name": "Wrong Pwd",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "wrongpwd@medai.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(auth_client: AsyncClient):
    """Test get current user."""
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@medai.com"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """Test get current user without token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_me(auth_client: AsyncClient):
    """Test updating current user account details."""
    response = await auth_client.put("/api/v1/auth/me", json={
        "full_name": "Updated Name",
        "phone": "+91 9876543210",
        "language_preference": "hi",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["phone"] == "+91 9876543210"
    assert data["language_preference"] == "hi"


@pytest.mark.asyncio
async def test_delete_me(auth_client: AsyncClient):
    """Test deleting current user account and data."""
    # Delete account
    response = await auth_client.delete("/api/v1/auth/me")
    assert response.status_code == 204

    # Verify user is deleted by attempting to get current user details
    get_me_response = await auth_client.get("/api/v1/auth/me")
    assert get_me_response.status_code == 401
