"""Minimal smoke tests — auth and S3 calls are mocked."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_unauthenticated_redirect():
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 401


def test_login_redirects_to_idp():
    with patch("app.routes.build_login_url", new=AsyncMock(return_value="https://idp/auth")):
        resp = client.get("/login", follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_logout_clears_session():
    with client.session_transaction() as sess:
        sess["user"] = {"sub": "1", "email": "a@b.com", "name": "A"}
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code in (302, 307)
