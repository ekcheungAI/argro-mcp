"""Smoke test for the health-check endpoint (no database required)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_routes_registered():
    paths = {route.path for route in app.routes}
    assert {
        "/news/stream",
        "/news/hot",
        "/news/{id}",
        "/insights/daily",
        "/meta/sources",
        "/meta/topics",
        "/healthz",
    } <= paths
