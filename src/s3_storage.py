"""
Identical to the cloud version's s3_storage.py -- only the boto3 client
creation changed, to point at LocalStack.
"""
import uuid
from datetime import datetime, timezone

import boto3

from src.config import BILLS_BUCKET, boto3_kwargs

_s3 = boto3.client("s3", **boto3_kwargs())


def store_bill(user_id: str, file_bytes: bytes, content_type: str) -> str:
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    key = f"bills/{date_prefix}/{user_id}/{uuid.uuid4()}"
    _s3.put_object(Bucket=BILLS_BUCKET, Key=key, Body=file_bytes, ContentType=content_type)
    return key