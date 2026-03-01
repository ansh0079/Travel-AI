"""
Tests for authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestUserRegistration:
    """Tests for user registration endpoint"""

    def test_register_success(self, client: TestClient):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with existing email fails"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "anotherpassword123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password fails validation"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short"  # Less than 8 characters
            }
        )
        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email format"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 422


class TestUserLogin:
    """Tests for user login endpoint"""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 401


class TestGetCurrentUser:
    """Tests for getting current user endpoint"""

    def test_get_me_authenticated(self, client: TestClient, auth_token: str):
        """Test getting current user with valid token"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_get_me_unauthenticated(self, client: TestClient):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401


class TestUserPreferences:
    """Tests for user preferences endpoints"""

    def test_get_preferences(self, client: TestClient, auth_token: str):
        """Test getting user preferences"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/auth/preferences", headers=headers)
        assert response.status_code == 200

    def test_update_preferences(self, client: TestClient, auth_token: str):
        """Test updating user preferences"""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        response = client.put(
            "/api/v1/auth/preferences",
            headers=headers,
            json={
                "budget_daily": 200.0,
                "budget_total": 4000.0,
                "travel_style": "comfort",
                "interests": ["nature", "food"],
                "passport_country": "US",
                "visa_preference": "visa_free",
                "traveling_with": "couple"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Preferences updated successfully"
        assert data["preferences"]["budget_daily"] == 200.0
