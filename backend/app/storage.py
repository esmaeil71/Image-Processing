import io
import uuid
from typing import BinaryIO, Optional

import boto3
from botocore.client import BaseClient

from app.config import settings


def _client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


def object_key(prefix: str, name: str) -> str:
    return f"{prefix}/{uuid.uuid4().hex}/{name}"


def upload_bytes(data: bytes, key: str, content_type: Optional[str] = None) -> str:
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    _client().put_object(Bucket=settings.s3_bucket, Key=key, Body=data, **extra)
    return key


def upload_stream(stream: BinaryIO, key: str, content_type: Optional[str] = None) -> str:
    data = stream.read()
    return upload_bytes(data, key, content_type)


def download_bytes(key: str) -> bytes:
    r = _client().get_object(Bucket=settings.s3_bucket, Key=key)
    return r["Body"].read()


def presign_get(key: str, expires: int = 3600) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires,
    )


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=settings.s3_bucket, Key=key)
