"""OIDC authentication via Authorization Code flow (authlib Starlette client)."""
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status
from starlette.config import Config

from .config import Settings, get_settings


def _make_oauth(settings: Settings) -> OAuth:
    config = Config(environ={
        "KEYCLOAK_CLIENT_ID": settings.oidc_client_id,
        "KEYCLOAK_CLIENT_SECRET": settings.oidc_client_secret,
    })
    oauth = OAuth(config)
    oauth.register(
        name="keycloak",
        server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


async def redirect_to_idp(request: Request, settings: Settings) -> Any:
    oauth = _make_oauth(settings)
    return await oauth.keycloak.authorize_redirect(request, settings.oidc_redirect_uri)


async def handle_callback(request: Request, settings: Settings) -> dict[str, Any]:
    oauth = _make_oauth(settings)
    token = await oauth.keycloak.authorize_access_token(request)
    user_info: dict[str, Any] = token.get("userinfo") or {}
    return user_info


def require_user(request: Request) -> dict[str, Any]:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
