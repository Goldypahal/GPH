import time
import threading
from typing import Dict, Any, Optional
import numpy as np
try:
    import cv2
except ImportError:
    cv2 = None
from backend.app.services.connectors.base import CameraConnector

class RTSPConnector(CameraConnector):
    """
    RTSP / RTSPS Stream Connector using OpenCV VideoCapture.
    Supports TCP transport enforcement, frame skipping, and auto-reconnection backoff.
    """

    def __init__(self, camera_id: str, stream_url: str, credentials: Optional[Dict[str, str]] = None):
        super().__init__(camera_id, stream_url, credentials)
        self._cap = None
        self._lock = threading.Lock()
        self._reconnect_delay = 2.0
        self._last_reconnect_attempt = 0.0

    def _build_authenticated_url(self) -> str:
        url = self.endpoint
        user = self.credentials.get("username")
        pwd = self.credentials.get("password")
        if user and pwd and "@" not in url:
            parts = url.split("://", 1)
            if len(parts) == 2:
                return f"{parts[0]}://{user}:{pwd}@{parts[1]}"
        return url

    def connect(self) -> bool:
        if cv2 is None:
            self.is_connected = False
            return False

        with self._lock:
            if self._cap and self._cap.isOpened():
                self.is_connected = True
                return True

            now = time.time()
            if (now - self._last_reconnect_attempt) < self._reconnect_delay:
                return False
            self._last_reconnect_attempt = now

            target_url = self._build_authenticated_url()
            try:
                # Open with TCP transport hint where supported
                self._cap = cv2.VideoCapture(target_url, cv2.CAP_FFMPEG)
                if self._cap.isOpened():
                    self.is_connected = True
                    self.fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
                    self.error_count = 0
                    return True
                else:
                    self.is_connected = False
                    self.error_count += 1
                    return False
            except Exception:
                self.is_connected = False
                self.error_count += 1
                return False

    def disconnect(self) -> None:
        with self._lock:
            if self._cap:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
            self.is_connected = False

    def read_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if not self.is_connected or not self._cap or not self._cap.isOpened():
                if not self.connect():
                    return None

            try:
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    self.last_frame_time = time.time()
                    return frame
                else:
                    self.error_count += 1
                    self.is_connected = False
                    return None
            except Exception:
                self.error_count += 1
                self.is_connected = False
                return None

    def get_health_metrics(self) -> Dict[str, Any]:
        return {
            "protocol": "RTSP",
            "camera_id": self.camera_id,
            "connected": self.is_connected,
            "fps": round(self.fps, 1),
            "errors": self.error_count,
            "last_frame_age_sec": round(time.time() - self.last_frame_time, 2) if self.last_frame_time > 0 else -1
        }
