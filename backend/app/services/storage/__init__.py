from typing import Optional
from backend.app.services.storage.base import ObjectStorage
from backend.app.services.storage.local_storage import LocalFileStorage
from backend.app.services.storage.minio_storage import MinIOStorage
from backend.app.core.config import settings

_storage_instance: Optional[ObjectStorage] = None

def get_storage() -> ObjectStorage:
    """
    Factory to retrieve the active ObjectStorage singleton.
    Falls back gracefully to LocalFileStorage if MinIO/S3 is configured but offline.
    """
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND in ("minio", "s3"):
            minio_instance = MinIOStorage()
            health = minio_instance.health_check()
            if health["status"] == "READY":
                _storage_instance = minio_instance
            else:
                # Graceful fallback for dev / local testing
                _storage_instance = LocalFileStorage()
        else:
            _storage_instance = LocalFileStorage()
    return _storage_instance

__all__ = ["ObjectStorage", "LocalFileStorage", "MinIOStorage", "get_storage"]
