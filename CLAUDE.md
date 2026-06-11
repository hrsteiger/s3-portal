# CLAUDE.md

## Project Overview

A minimal FastAPI portal that authenticates users via OIDC (Authorization Code flow) and
lets them browse and download files from an S3-compatible bucket. There is one role:
authenticated user (session-based, cookie).

## Commands

```bash
# Setup
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e ".[dev]"
cp .env.example .env    # fill in real values

# Run
uvicorn app.main:app --reload --port 8000
docker-compose up --build   # full stack incl. local MinIO

# Test
pytest

# Lint / type-check
ruff check .
mypy app/
```

## Key files

- `app/config.py` — all settings via pydantic-settings / `.env`
- `app/auth.py`  — OIDC login, callback, `require_user` dependency
- `app/s3.py`    — `list_objects`, `presign_download` via aioboto3
- `app/routes.py` — thin FastAPI router; business logic stays in `s3.py` / `auth.py`
- `templates/index.html` — plain HTML table of bucket contents

## Conventions

- Single role: any authenticated session = authorized.
- Pre-signed URLs for downloads — the app never proxies file bytes.
- Settings read only through `get_settings()` (cached); never `os.environ` directly.
