"""Structured audit logging for upload and download events.

Each event is emitted as a single JSON line to the 's3_portal.audit' logger so it
can be forwarded to any log aggregator (Loki, CloudWatch, stdout in k8s, etc.).

Example output:
  {"event": "download", "key": "reports/q1.csv", "user": "alice@example.com",
   "sub": "abc123", "ip": "10.0.0.5", "ts": "2026-06-11T07:42:00.123456+00:00"}
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("s3_portal.audit")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client_ip(request) -> str:
    # Respect X-Forwarded-For when behind an ingress / load balancer
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def log_download(request, key: str, user: dict) -> None:
    logger.info(json.dumps({
        "event": "download",
        "key": key,
        "user": user.get("email", ""),
        "sub": user.get("sub", ""),
        "ip": _client_ip(request),
        "ts": _now(),
    }))


def log_upload(request, key: str, size: int) -> None:
    logger.info(json.dumps({
        "event": "upload",
        "key": key,
        "size": size,
        "ip": _client_ip(request),
        "ts": _now(),
    }))


def log_login(request, user: dict) -> None:
    logger.info(json.dumps({
        "event": "login",
        "user": user.get("email", ""),
        "sub": user.get("sub", ""),
        "ip": _client_ip(request),
        "ts": _now(),
    }))


def log_logout(request, user: dict) -> None:
    logger.info(json.dumps({
        "event": "logout",
        "user": user.get("email", ""),
        "sub": user.get("sub", ""),
        "ip": _client_ip(request),
        "ts": _now(),
    }))
