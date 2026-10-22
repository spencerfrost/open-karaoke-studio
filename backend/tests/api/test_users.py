"""
Tests for FastAPI users endpoints.
"""

from app.db.models import User


class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/users/register",
            json={
                "username": "testuser",
                "display_name": "Test User",
                "password": "testpass123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_register_requires_username(self, client):
        """Test that username is required."""
        response = client.post(
            "/api/users/register",
            json={"display_name": "Test User", "password": "testpass123"},
        )

        assert response.status_code == 422

    def test_register_requires_password(self, client):
        """Test that password is required."""
        response = client.post("/api/users/register", json={"username": "testuser"})

        assert response.status_code == 422

    def test_register_password_min_length(self, client):
        """Test that password must be at least 8 characters."""
        response = client.post(
            "/api/users/register", json={"username": "testuser", "password": "short"}
        )

        assert response.status_code == 422

    def test_register_username_already_exists(self, client, db):
        """Test registration fails when username exists."""
        existing = User(username="existinguser")
        existing.set_password("password123")
        db.add(existing)
        db.commit()

        response = client.post(
            "/api/users/register",
            json={"username": "existinguser", "password": "password123"},
        )

        assert response.status_code == 400
        assert "exists" in response.json()["detail"].lower()


class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client, db):
        """Test successful login with correct credentials."""
        user = User(username="testuser", display_name="Test User")
        user.set_password("correctpassword")
        user.is_admin = False
        user.is_host = False
        db.add(user)
        db.commit()

        response = client.post(
            "/api/users/login",
            json={"username": "testuser", "password": "correctpassword"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["display_name"] == "Test User"
        assert "token" in data

    def test_login_requires_username(self, client):
        """Test that username is required."""
        response = client.post("/api/users/login", json={"password": "somepassword"})

        assert response.status_code == 422

    def test_login_requires_password(self, client):
        """Test that password is required."""
        response = client.post("/api/users/login", json={"username": "testuser"})

        assert response.status_code == 422

    def test_login_invalid_username(self, client):
        """Test login fails with non-existent username."""
        response = client.post(
            "/api/users/login",
            json={"username": "nonexistent", "password": "somepassword"},
        )

        assert response.status_code == 401

    def test_login_wrong_password(self, client, db):
        """Test login fails with wrong password."""
        user = User(username="testuser2")
        user.set_password("correctpassword")
        db.add(user)
        db.commit()

        response = client.post(
            "/api/users/login",
            json={"username": "testuser2", "password": "wrongpassword"},
        )

        assert response.status_code == 401


class TestUserUpdate:
    """Tests for user update endpoint."""

    def test_update_display_name(self, client, db):
        """Test updating display name."""
        user = User(username="updateuser")
        user.set_password("password123")
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.patch(
            f"/api/users/{user.id}", json={"display_name": "New Display Name"}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        db.refresh(user)
        assert user.display_name == "New Display Name"

    def test_update_password(self, client, db):
        """Test updating password."""
        user = User(username="pwupdateuser")
        user.set_password("oldpassword")
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.patch(
            f"/api/users/{user.id}", json={"password": "newpassword123"}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_update_password_too_short(self, client, db):
        """Test that updated password must be at least 8 characters."""
        user = User(username="shortpwuser")
        user.set_password("password123")
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.patch(f"/api/users/{user.id}", json={"password": "short"})

        assert response.status_code == 422

    def test_update_requires_at_least_one_field(self, client, db):
        """Test that at least one field must be provided."""
        user = User(username="emptyupdateuser")
        user.set_password("password123")
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.patch(f"/api/users/{user.id}", json={})

        assert response.status_code == 400

    def test_update_user_not_found(self, client):
        """Test update fails when user not found."""
        response = client.patch("/api/users/99999", json={"display_name": "Test"})

        assert response.status_code == 404

    def test_update_demo_account_forbidden(self, client, db):
        """Demo pool accounts can't be modified (prevents password hijack)."""
        user = User(username="demo-pool-x")
        user.set_password("password123")
        user.is_demo = True
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.patch(
            f"/api/users/{user.id}", json={"password": "newpassword123"}
        )

        assert response.status_code == 403

    def test_update_requires_auth(self, client, fastapi_app):
        """Test that update endpoint requires authentication."""
        from fastapi import HTTPException

        from app.api.dependencies import get_current_user

        def require_auth():
            raise HTTPException(status_code=401, detail="Not authenticated")

        fastapi_app.dependency_overrides[get_current_user] = require_auth
        try:
            response = client.patch("/api/users/1", json={"display_name": "Test"})
            assert response.status_code == 401
        finally:
            from tests.api.conftest import _get_mock_user

            fastapi_app.dependency_overrides[get_current_user] = _get_mock_user
