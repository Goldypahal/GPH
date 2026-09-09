import io
from typing import Dict, Any, Optional
from datetime import timedelta
from backend.app.services.storage.base import ObjectStorage
from backend.app.core.config import settings

class MinIOStorage(ObjectStorage):
    """
    Production-grade MinIO / S3 Object Storage Driver.
    Stores full resolution camera snapshot frames, plate crops, and export evidence packages.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        try:
            from minio import Minio
            self.endpoint = endpoint or settings.MINIO_ENDPOINT
            self.access_key = access_key or settings.MINIO_ACCESS_KEY
            self.secret_key = secret_key or settings.MINIO_SECRET_KEY
            self.secure = secure if secure is not None else settings.MINIO_SECURE

            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            self._ensure_bucket(settings.MINIO_BUCKET_EVIDENCE)
            self._available = True
        except Exception as e:
            self.client = None
            self._available = False
            self._init_error = str(e)

    def _ensure_bucket(self, bucket: str):
        if self.client and not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        if not self.client:
            raise RuntimeError(f"MinIO client unavailable: {getattr(self, '_init_error', 'Not connected')}")
        self._ensure_bucket(bucket)
        stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=bucket,
            object_name=key,
            data=stream,
            length=len(data),
            content_type=content_type
        )
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}/{bucket}/{key}"

    def get_object(self, bucket: str, key: str) -> Optional[bytes]:
        if not self.client:
            return None
        try:
            response = self.client.get_object(bucket, key)
            return response.read()
        except Exception:
            return None
        finally:
            if 'response' in locals() and response:
                response.close()
                response.release_conn()

    def get_presigned_url(self, bucket: str, key: str, expires_seconds: int = 3600) -> str:
        if not self.client:
            return f"/api/evidence/download/{bucket}/{key}"
        try:
            return self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=key,
                expires=timedelta(seconds=expires_seconds)
            )
        except Exception:
            return f"/api/evidence/download/{bucket}/{key}"

    def delete_object(self, bucket: str, key: str) -> bool:
        if not self.client:
            return False
        try:
            self.client.remove_object(bucket, key)
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        if not self.client:
            return {
                "status": "UNAVAILABLE",
                "backend": "MINIO_S3",
                "error": getattr(self, "_init_error", "Client not initialized")
            }
        try:
            buckets = [b.name for b in self.client.list_buckets()]
            return {
                "status": "READY",
                "backend": "MINIO_S3",
                "endpoint": self.endpoint,
                "buckets": buckets
            }
        except Exception as e:
            return {
                "status": "DEGRADED",
                "backend": "MINIO_S3",
                "endpoint": self.endpoint,
                "error": str(e)
            }
