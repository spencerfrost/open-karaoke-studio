"""
Tests for FastAPI users endpoints.
"""

from unittest.mock import MagicMock, Mock

import pytest


class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_user_success(self, client, mock_user_db):
        """Test successful user registration."""
        # Mock user creation
        mock_user = Mock()
        mock_user.id = 1
        mock_user_db.add = Mock()
        mock_user_db.commit = Mock()
        
        response = client.post(
            "/api/users/register",
            json={
                "username": "testuser",
                "display_name": "Test User",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_register_requires_username(self, client):
        """Test that username is required."""
        response = client.post(
            "/api/users/register",
            json={"display_name": "Test User"}
        )
        
        assert response.status_code == 422

    def test_register_username_already_exists(self, client, mock_user_db):
        """Test registration fails when username exists."""
        # Mock existing user
        existing_user = Mock()
        mock_user_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        response = client.post(
            "/api/users/register",
            json={"username": "existinguser"}
        )
        
        assert response.status_code == 400
        assert "exists" in response.json()["detail"].lower()

    def test_register_without_password(self, client, mock_user_db):
        """Test registration without password (passwordless user)."""
        mock_user_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.post(
            "/api/users/register",
            json={"username": "testuser"}
        )
        
        # Should succeed - password is optional
        assert response.status_code == 201


class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success_without_password(self, client, mock_user_db):
        """Test successful login for passwordless user."""
        # Mock user without password
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.display_name = "Test User"
        mock_user.password_hash = None
        mock_user.is_admin = False
        mock_user.is_host = False
        mock_user_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        response = client.post(
            "/api/users/login",
            json={"username": "testuser"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["display_name"] == "Test User"

    def test_login_success_with_password(self, client, mock_user_db):
        """Test successful login with password."""
        # Mock user with password
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.display_name = "Test User"
        mock_user.password_hash = "hashed_password"
        mock_user.is_admin = False
        mock_user.is_host = False
        mock_user.check_password.return_value = True
        mock_user_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        response = client.post(
            "/api/users/login",
            json={"username": "testuser", "password": "correctpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_login_requires_username(self, client):
        """Test that username is required."""
        response = client.post(
            "/api/users/login",
            json={"password": "somepassword"}
        )
        
        assert response.status_code == 422

    def test_login_invalid_username(self, client, mock_user_db):
        """Test login fails with invalid username."""
        mock_user_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.post(
            "/api/users/login",
            json={"username": "nonexistent"}
        )
        
        assert response.status_code == 401

    def test_login_wrong_password(self, client, mock_user_db):
        """Test login fails with wrong password."""
        mock_user = Mock()
        mock_user.password_hash = "hashed_password"
        mock_user.check_password.return_value = False
        mock_user_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        response = client.post(
            "/api/users/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401


class TestUserUpdate:
    """Tests for user update endpoint."""

    def test_update_display_name(self, client, mock_user_db):
        """Test updating display name."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        response = client.patch(
            "/api/users/1",
            json={"display_name": "New Display Name"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert mock_user.display_name == "New Display Name"

    def test_update_password(self, client, mock_user_db):
        """Test updating password."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        response = client.patch(
            "/api/users/1",
            json={"password": "newpassword123"}
        )
        
        assert response.status_code == 200
        mock_user.set_password.assert_called_once_with("newpassword123")

    def test_update_requires_at_least_one_field(self, client):
        """Test that at least one field must be provided."""
        response = client.patch(
            "/api/users/1",
            json={}
        )
        
        assert response.status_code == 400

    def test_update_user_not_found(self, client, mock_user_db):
        """Test update fails when user not found."""
        mock_user_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.patch(
            "/api/users/999",
            json={"display_name": "Test"}
        )
        
        assert response.status_code == 404
