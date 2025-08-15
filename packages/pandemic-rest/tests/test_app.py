"""Tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from pandemic_rest import create_app


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "daemon": {"socket_path": "/tmp/test-pandemic.sock"},
        "auth": {"jwt_secret": "test-secret", "jwt_expiry": 3600},
        "user_management": {
            "provider": "local",
            "local": {
                "users_file": "/tmp/test-users.yaml",
                "role_mapping": {"admin": "admin", "user": "read-only"},
            },
        },
        "cors": {"enabled": True, "origins": ["*"]},
        "logging": {"level": "INFO"},
    }


@pytest.fixture
def app(test_config):
    """Create test FastAPI app."""
    return create_app(test_config)


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Pandemic REST API"
    assert data["version"] == "1.0.0"


def test_health_endpoint_no_daemon(client):
    """Test health endpoint when daemon is not running."""
    response = client.get("/api/v1/health")
    # Should return 503 when daemon is not available
    assert response.status_code == 503


def test_openapi_docs(client):
    """Test OpenAPI documentation endpoint."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_login_endpoint_no_users_file(client):
    """Test login endpoint when users file doesn't exist."""
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "password"})
    # Should return 401 when user not found
    assert response.status_code == 401
