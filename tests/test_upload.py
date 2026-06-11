"""Unit tests for the /upload endpoint — S3 is mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

GOOD_KEY = "test-api-key-value"

client = TestClient(app)


def _settings_override():
    from app.config import Settings
    return Settings(
        s3_bucket="test-bucket",
        s3_region="us-east-1",
        aws_access_key_id="x",
        aws_secret_access_key="x",
        oidc_issuer="https://idp.example.com",
        oidc_client_id="cid",
        oidc_client_secret="csec",
        oidc_redirect_uri="http://localhost/auth/callback",
        upload_api_key=GOOD_KEY,
        secret_key="test-secret",
    )


@pytest.fixture(autouse=True)
def override_settings():
    from app.config import get_settings
    app.dependency_overrides[get_settings] = _settings_override
    yield
    app.dependency_overrides.clear()


def test_upload_missing_key_is_rejected():
    resp = client.post("/upload/my/file.txt", content=b"hello")
    assert resp.status_code == 401


def test_upload_wrong_key_is_rejected():
    resp = client.post("/upload/my/file.txt", content=b"hello",
                       headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_upload_empty_body_is_rejected():
    resp = client.post("/upload/my/file.txt", content=b"",
                       headers={"X-API-Key": GOOD_KEY})
    assert resp.status_code == 422


@patch("app.upload._put_object", new_callable=AsyncMock)
def test_upload_success(mock_put):
    resp = client.post(
        "/upload/reports/data.csv",
        content=b"col1,col2\n1,2\n",
        headers={"X-API-Key": GOOD_KEY, "Content-Type": "text/csv"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"] == "reports/data.csv"
    assert body["size"] == 15
    mock_put.assert_awaited_once()
