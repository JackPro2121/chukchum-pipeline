import boto3
import uuid
from pathlib import Path
from config import R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_PUBLIC_BASE


class MediaHostError(RuntimeError):
    pass


def upload_public(file_path: str) -> str:
    if not all([R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_PUBLIC_BASE]):
        raise MediaHostError("R2 env vars not set. Set R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_PUBLIC_BASE.")
    client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
    )
    key = f"videos/{uuid.uuid4().hex}.mp4"
    client.upload_file(file_path, R2_BUCKET, key, ExtraArgs={"ContentType": "video/mp4", "ACL": "public-read"})
    return f"{R2_PUBLIC_BASE}/{key}"
