from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # S3
    s3_endpoint_url: str = ""          # leave empty for AWS; set for MinIO
    s3_bucket: str
    s3_region: str = "us-east-1"
    aws_access_key_id: str
    aws_secret_access_key: str

    # OIDC (human users)
    oidc_issuer: str                   # e.g. https://accounts.google.com
    oidc_client_id: str
    oidc_client_secret: str
    oidc_redirect_uri: str             # e.g. http://localhost:8000/auth/callback

    # In-cluster service auth
    upload_api_key: str                # mount from a K8s Secret in production

    # Session signing key
    secret_key: str = "change-me-in-production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
