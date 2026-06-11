"""In-cluster upload endpoint.

Security model
--------------
1. Application layer  — X-API-Key header matched against UPLOAD_API_KEY (constant-time compare).
2. Network layer      — a Kubernetes NetworkPolicy (see k8s/networkpolicy.yaml) restricts
                        which pods may reach this service at all; a stolen key from outside
                        the cluster is therefore useless.

Usage from a pod
----------------
  curl -X POST http://s3-portal/upload/my-dir/report.csv \
       -H "X-API-Key: $UPLOAD_API_KEY" \
       --data-binary @report.csv
"""
import hmac
import mimetypes
from typing import Annotated

import aioboto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from .config import Settings, get_settings

router = APIRouter(prefix="/upload", tags=["upload"])

_MAX_BYTES = 100 * 1024 * 1024  # 100 MB hard limit


def _verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency: validates X-API-Key using a timing-safe compare."""
    if x_api_key is None or not hmac.compare_digest(x_api_key, settings.upload_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


async def _put_object(key: str, body: bytes, content_type: str, settings: Settings) -> None:
    session = aioboto3.Session(
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.s3_region,
    )
    kwargs = {"endpoint_url": settings.s3_endpoint_url} if settings.s3_endpoint_url else {}
    async with session.client("s3", **kwargs) as client:
        try:
            await client.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
            )
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"S3 error: {exc}",
            ) from exc


@router.post(
    "/{key:path}",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_api_key)],
    summary="Push a file to S3 (in-cluster service auth)",
)
async def upload_file(
    key: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Upload raw bytes to `s3://<bucket>/<key>`.

    - `key` may contain path segments: `my-service/2024/data.csv`
    - Body size is capped at 100 MB.
    - Content-Type is inferred from the key extension when not supplied.
    """
    body = await request.body()
    if len(body) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty body")
    if len(body) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Body exceeds {_MAX_BYTES // (1024*1024)} MB limit",
        )

    content_type = (
        request.headers.get("content-type")
        or mimetypes.guess_type(key)[0]
        or "application/octet-stream"
    )
    await _put_object(key, body, content_type, settings)
    return {"key": key, "bucket": settings.s3_bucket, "size": len(body)}
