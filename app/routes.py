from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .audit import log_download, log_login, log_logout
from .auth import handle_callback, redirect_to_idp, require_user
from .config import Settings, get_settings
from .s3 import list_objects, presign_download

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.get("/login")
async def login(request: Request, settings: Settings = Depends(get_settings)):
    return await redirect_to_idp(request, settings)


@router.get("/auth/callback")
async def auth_callback(request: Request, settings: Settings = Depends(get_settings)):
    user_info = await handle_callback(request, settings)
    user = {
        "sub": user_info.get("sub", ""),
        "email": user_info.get("email", ""),
        "name": user_info.get("name") or user_info.get("preferred_username") or user_info.get("email", "user"),
    }
    request.session["user"] = user
    log_login(request, user)
    return RedirectResponse("/")


@router.get("/logout")
async def logout(request: Request):
    user = request.session.get("user", {})
    log_logout(request, user)
    request.session.clear()
    return RedirectResponse("/login")


# ── Portal ────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    user: dict = Depends(require_user),
    settings: Settings = Depends(get_settings),
):
    objects = await list_objects(settings)
    return templates.TemplateResponse(
        request, "index.html", {"user": user, "objects": objects}
    )


@router.get("/download/{key:path}")
async def download(
    key: str,
    user: dict = Depends(require_user),
    settings: Settings = Depends(get_settings),
    request: Request = None,
):
    log_download(request, key, user)
    url = await presign_download(key, settings)
    return RedirectResponse(url)
