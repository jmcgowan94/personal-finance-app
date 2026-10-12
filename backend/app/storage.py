"""Storage for the raw uploaded statement files.

Keys are laid out as ``users/<user_id>/uploads/<uuid>.csv`` so that the same keys
work as local paths and as S3 object keys.
"""

import uuid
from pathlib import Path
from typing import Protocol

from app.config import Settings, get_settings


class Storage(Protocol):
    def save(self, user_id: int, data: bytes) -> str: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


def new_key(user_id: int) -> str:
    return f"users/{user_id}/uploads/{uuid.uuid4().hex}.csv"


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Invalid storage key")
        return path

    def save(self, user_id: int, data: bytes) -> str:
        key = new_key(user_id)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage:
    def __init__(self, bucket: str):
        import boto3  # optional dependency: `uv sync --extra aws`

        self.bucket = bucket
        self.client = boto3.client("s3")

    def save(self, user_id: int, data: bytes) -> str:
        key = new_key(user_id)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def read(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set when STORAGE_BACKEND=s3")
        return S3Storage(settings.s3_bucket)
    return LocalStorage(settings.local_storage_dir)


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = build_storage(get_settings())
    return _storage
