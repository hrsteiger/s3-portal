import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .routes import router
from .upload import router as upload_router

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "loggers": {
        "s3_portal.audit": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
    "root": {"level": "INFO", "handlers": ["console"]},
})

settings = get_settings()

app = FastAPI(title="S3 Portal")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.include_router(router)
app.include_router(upload_router)


@app.exception_handler(HTTPException)
async def redirect_unauthenticated(request: Request, exc: HTTPException):
    # Browser UI routes: redirect 401 to /login instead of returning JSON
    if exc.status_code == 401 and not request.url.path.startswith("/upload"):
        return RedirectResponse(url="/login")
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
