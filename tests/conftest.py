"""Shared pytest fixtures."""

import os

# Provide a dummy DATABASE_URL so the app can be imported even without a .env file.
# Tests that need a real database will configure their own in later stages.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test_db")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
