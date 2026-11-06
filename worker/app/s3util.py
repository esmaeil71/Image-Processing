import io
from typing import BinaryIO

import boto3

from app.config import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


def download_bytes(key: str) -> bytes:
    r = _client().get_object(Bucket=settings.s3_bucket, Key=key)
    return r["Body"].read()


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> None:
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    _client().put_object(Bucket=settings.s3_bucket, Key=key, Body=data, **extra)


def upload_stream(key: str, stream: BinaryIO, content_type: str | None = None) -> None:
    upload_bytes(key, stream.read(), content_type)
