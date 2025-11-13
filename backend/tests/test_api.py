"""
Test API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_get_emails():
    """Test lista email"""
    response = client.get("/api/emails")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_email_stats():
    """Test statistiche"""
    response = client.get("/api/emails/stats")
    assert response.status_code == 200
    data = response.json()
    assert "today" in data
    assert "week" in data
