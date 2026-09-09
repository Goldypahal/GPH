from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np

class CameraConnector(ABC):
    """
    Abstract Protocol Connector for CCTV Video Ingestion.
    Decouples vision AI pipeline from physical stream transport (RTSP, RTSPS, ONVIF, VMS, HTTP).
    """

    def __init__(self, camera_id: str, endpoint: str, credentials: Optional[Dict[str, str]] = None):
        self.camera_id = camera_id
        self.endpoint = endpoint
        self.credentials = credentials or {}
        self.is_connected = False
        self.fps = 0.0
        self.last_frame_time = 0.0
        self.error_count = 0

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the video stream source."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully tears down the socket/connection."""
        pass

    @abstractmethod
    def read_frame(self) -> Optional[np.ndarray]:
        """Fetches the latest decoded video frame as a BGR numpy array."""
        pass

    @abstractmethod
    def get_health_metrics(self) -> Dict[str, Any]:
        """Returns protocol-level telemetry (FPS, packet drop, latency)."""
        pass
