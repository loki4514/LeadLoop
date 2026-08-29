"""Upload storage: local disk for dev, S3-compatible object storage for prod.

The API container writes uploads and the Celery worker reads them back, and on
a platform like Railway those are separate filesystems — a local path written by
one is missing for the other. When R2/S3 is configured, uploads go to a bucket
both containers can reach; ``Document.storage_path`` then holds an ``r2://<key>``
URI instead of a filesystem path.

With no bucket configured this falls back to local disk, so docker-compose (which
shares one volume between the two services) and local dev keep working unchanged.
"""
import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import BinaryIO, Iterator

from app.core.config import settings

R2_SCHEME = "r2://"


def is_object_storage_enabled() -> bool:
    return bool(settings.S3_BUCKET and settings.S3_ENDPOINT_URL)


def _client():
    """Build an S3 client. Imported lazily so boto3 is only needed in prod."""
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        # R2 only supports the newer signature version.
        config=Config(signature_version="s3v4"),
    )


def save_upload(fileobj: BinaryIO, stored_name: str) -> str:
    """Persist an uploaded file and return the value for ``storage_path``.

    ``fileobj`` must be positioned at the start.
    """
    if not is_object_storage_enabled():
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        path = os.path.join(settings.UPLOAD_DIR, stored_name)
        with open(path, "wb") as out:
            shutil.copyfileobj(fileobj, out)
        return path

    key = f"{settings.S3_PREFIX}{stored_name}" if settings.S3_PREFIX else stored_name
    _client().upload_fileobj(fileobj, settings.S3_BUCKET, key)
    return f"{R2_SCHEME}{key}"


@contextmanager
def local_copy(storage_path: str) -> Iterator[str]:
    """Yield a filesystem path for ``storage_path``.

    Local paths are yielded as-is. Object-storage URIs are downloaded to a temp
    file that is removed on exit — MarkItDown needs a real path, and streaming
    it straight from the bucket would mean reimplementing its format sniffing.
    """
    if not storage_path.startswith(R2_SCHEME):
        yield storage_path
        return

    key = storage_path[len(R2_SCHEME) :]
    suffix = os.path.splitext(key)[1]
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        _client().download_file(settings.S3_BUCKET, key, tmp)
        yield tmp
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def delete_upload(storage_path: str) -> None:
    """Best-effort removal of a stored upload."""
    if storage_path.startswith(R2_SCHEME):
        key = storage_path[len(R2_SCHEME) :]
        _client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
        return
    try:
        os.remove(storage_path)
    except OSError:
        pass
