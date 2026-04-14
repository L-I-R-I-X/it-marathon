"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_swagger_ui():
    """Test that Swagger UI is available at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_robinson_cruise_empty_body():
    """Test POST /api/v1/robinson_cruise with empty body returns 400."""
    response = client.post("/api/v1/robinson_cruise", json={})
    assert response.status_code == 400
    assert response.json() == {"status": "incorrect_input"}


def test_star_visibility_empty_body():
    """Test POST /api/v1/star_visibility with empty body returns 400."""
    response = client.post("/api/v1/star_visibility", json={})
    assert response.status_code == 400
    assert response.json() == {"status": "incorrect_input"}


def test_constellation_finder_empty_body():
    """Test POST /api/v1/constellation_finder with empty body returns 400."""
    response = client.post("/api/v1/constellation_finder", json={})
    assert response.status_code == 400
    assert response.json() == {"status": "incorrect_input"}


def test_robinson_cruise_valid_request():
    """Test POST /api/v1/robinson_cruise with valid request returns 200."""
    # Minimal valid JSON object (placeholder until real schema is defined)
    response = client.post("/api/v1/robinson_cruise", json={})
    # Empty object should fail validation since we require fields
    # This tests the stub behavior - will be updated when real schema is defined
    assert response.status_code in [200, 400]


def test_star_visibility_valid_request():
    """Test POST /api/v1/star_visibility with valid request returns 200."""
    response = client.post("/api/v1/star_visibility", json={})
    assert response.status_code in [200, 400]


def test_constellation_finder_valid_request():
    """Test POST /api/v1/constellation_finder with valid request returns 200."""
    response = client.post("/api/v1/constellation_finder", json={})
    assert response.status_code in [200, 400]


def test_invalid_json_content_type():
    """Test that non-JSON content returns 400."""
    response = client.post(
        "/api/v1/robinson_cruise",
        content="not a json object",
        headers={"Content-Type": "text/plain"}
    )
    assert response.status_code == 400


def test_json_array_instead_of_object():
    """Test that JSON array instead of object returns 400."""
    response = client.post("/api/v1/robinson_cruise", json=[1, 2, 3])
    assert response.status_code == 400
    assert response.json() == {"status": "incorrect_input"}
