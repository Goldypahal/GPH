import os
import shutil
from typing import Dict, Any, Optional
from backend.app.services.storage.base import ObjectStorage
from backend.app.core.config import settings

class LocalFileStorage(ObjectStorage):
    """
    Local filesystem storage driver for offline testing, edge buffers,
    and developer environments without active MinIO/S3 daemon.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.EVIDENCE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, bucket: str, key: str) -> str:
        # Sanitize key to prevent path traversal
        clean_key = os.path.normpath(key).lstrip("/\\")
        bucket_dir = os.path.join(self.base_dir, bucket)
        os.makedirs(bucket_dir, exist_ok=True)
        return os.path.join(bucket_dir, clean_key)

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        file_path = self._resolve_path(bucket, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        return f"file://{file_path.replace(os.sep, '/')}"

    def get_object(self, bucket: str, key: str) -> Optional[bytes]:
        file_path = self._resolve_path(bucket, key)
        if not os.path.exists(file_path):
            return None
        with open(file_path, "rb") as f:
            return f.read()

    def get_presigned_url(self, bucket: str, key: str, expires_seconds: int = 3600) -> str:
        # For local file storage, return the direct API evidence URL
        return f"/api/evidence/download/{bucket}/{key}"

    def delete_object(self, bucket: str, key: str) -> bool:
        file_path = self._resolve_path(bucket, key)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def health_check(self) -> Dict[str, Any]:
        try:
            test_file = os.path.join(self.base_dir, ".health_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return {
                "status": "READY",
                "backend": "LOCAL_FILESYSTEM",
                "base_dir": self.base_dir,
                "writable": True
            }
        except Exception as e:
            return {
                "status": "DEGRADED",
                "backend": "LOCAL_FILESYSTEM",
                "error": str(e)
            }
