"""
Tests for the authentication router.

Covers POST /auth/login and GET /auth/me.
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    """Tests for credential validation and JWT issuance."""

    def test_valid_credentials_returns_200_with_token(self, client: TestClient) -> None:
        """A correct email/password pair returns a JWT access token."""
        response = client.post(
            "/auth/login",
            json={"email": "alice@finsolve.com", "password": "password123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert len(body["access_token"]) > 0
        assert body["token_type"] == "bearer"
        assert body["role"] == "finance"
        assert body["email"] == "alice@finsolve.com"

    def test_wrong_password_returns_401(self, client: TestClient) -> None:
        """A valid email with the wrong password is rejected."""
        response = client.post(
            "/auth/login",
            json={"email": "alice@finsolve.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_nonexistent_email_returns_401(self, client: TestClient) -> None:
        """An email that does not exist in the store is rejected with the same message."""
        response = client.post(
            "/auth/login",
            json={"email": "nobody@finsolve.com", "password": "password123"},
        )
        assert response.status_code == 401
        # Same message as wrong-password to prevent user enumeration.
        assert response.json()["detail"] == "Incorrect email or password"

    def test_missing_password_returns_422(self, client: TestClient) -> None:
        """A request body missing the password field fails pydantic validation."""
        response = client.post(
            "/auth/login",
            json={"email": "alice@finsolve.com"},
        )
        assert response.status_code == 422

    def test_missing_email_returns_422(self, client: TestClient) -> None:
        """A request body missing the email field fails pydantic validation."""
        response = client.post(
            "/auth/login",
            json={"password": "password123"},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        """An entirely empty body fails pydantic validation."""
        response = client.post("/auth/login", json={})
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "email,expected_role",
        [
            ("alice@finsolve.com",  "finance"),
            ("bob@finsolve.com",    "engineering"),
            ("carol@finsolve.com",  "hr"),
            ("david@finsolve.com",  "marketing"),
            ("eve@finsolve.com",    "employee"),
            ("frank@finsolve.com",  "c_level"),
        ],
    )
    def test_all_seeded_users_can_login(
        self, client: TestClient, email: str, expected_role: str
    ) -> None:
        """Every pre-seeded user can authenticate and receives the correct role."""
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "password123"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == expected_role


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


class TestGetMe:
    """Tests for the token-introspection endpoint."""

    def test_valid_token_returns_email_and_role(
        self, client: TestClient, token_finance: str
    ) -> None:
        """A valid JWT returns the caller's email and role."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token_finance}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "alice@finsolve.com"
        assert body["role"] == "finance"

    def test_no_token_returns_401(self, client: TestClient) -> None:
        """A request without an Authorization header is rejected."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """A malformed or tampered JWT is rejected."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )
        assert response.status_code == 401

    def test_malformed_bearer_header_returns_401(self, client: TestClient) -> None:
        """An Authorization header without the Bearer prefix is rejected."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Token sometoken"},
        )
        assert response.status_code == 401

    def test_me_reflects_correct_role_for_each_user(
        self, client: TestClient, token_c_level: str
    ) -> None:
        """The role returned by /auth/me matches the role embedded in the token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token_c_level}"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "c_level"
