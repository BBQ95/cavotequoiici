"""Fixtures partagées des tests API."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    """Client de test FastAPI (in-process)."""
    return TestClient(app)
