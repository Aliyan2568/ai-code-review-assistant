"""Tests for the root and health endpoints. The database check is mocked."""

from unittest.mock import patch

from sqlalchemy.exc import OperationalError


def test_root_returns_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"]


def test_health_ok_when_database_connected(client):
    with patch("app.routes.health.check_db_connection", return_value=True):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_503_when_database_down(client):
    error = OperationalError("SELECT 1", {}, Exception("connection refused"))
    with patch("app.routes.health.check_db_connection", side_effect=error):
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}
