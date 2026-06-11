from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aioboto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from .config import Settings


@asynccontextmanager
async def _s3_client(settings: Settings) -> AsyncGenerator:
    session = aioboto3.Session(
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.s3_region,
    )
    kwargs = {}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    async with session.client("s3", **kwargs) as client:
        yield client


async def list_objects(settings: Settings) -> list[dict]:
    """Return a list of {key, size, last_modified} dicts."""
    async with _s3_client(settings) as client:
        try:
            paginator = client.get_paginator("list_objects_v2")
            items: list[dict] = []
            async for page in paginator.paginate(Bucket=settings.s3_bucket):
                for obj in page.get("Contents", []):
                    items.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                        }
                    )
            return items
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"S3 error: {exc}",
            ) from exc


async def presign_download(key: str, settings: Settings, expires: int = 300) -> str:
    """Generate a pre-signed URL for a single object (default 5 min)."""
    async with _s3_client(settings) as client:
        try:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.s3_bucket, "Key": key},
                ExpiresIn=expires,
            )
            return url
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"S3 error: {exc}",
            ) from exc
