from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class WORMImmutableViolationError(RuntimeError):
    """Raised when an attempt is made to overwrite or delete a WORM-locked evidence object."""
    pass

class ObjectStorage(ABC):

    """
    Abstract Storage Interface for GIVIN Evidence and Media artifacts.
    Decouples storage consumer services from physical backends (MinIO, AWS S3, Ceph, Local).
    """

    @abstractmethod
    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """Uploads bytes and returns the stored URI/path."""
        pass

    @abstractmethod
    def get_object(self, bucket: str, key: str) -> Optional[bytes]:
        """Retrieves raw object bytes."""
        pass

    @abstractmethod
    def get_presigned_url(self, bucket: str, key: str, expires_seconds: int = 3600) -> str:
        """Generates a temporary pre-signed URL for browser viewing/download."""
        pass

    @abstractmethod
    def delete_object(self, bucket: str, key: str) -> bool:
        """Deletes an object."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Returns connectivity and health status."""
        pass
