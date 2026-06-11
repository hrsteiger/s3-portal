"""Smoke tests for UI routes — OIDC and S3 calls are mocked."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_unauthenticated_redirects_to_login():
    # exception handler converts 401 → 307 redirect to /login
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "/login"


def test_login_redirects_to_idp():
    fake_redirect = RedirectResponse(url="https://idp/auth")
    with patch("app.routes.redirect_to_idp", new=AsyncMock(return_value=fake_redirect)):
        resp = client.get("/login", follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_logout_redirects_to_login():
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "/login" in resp.headers["location"]
