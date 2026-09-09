import time
from typing import Dict, Any, Optional
import numpy as np
from backend.app.services.connectors.base import CameraConnector
from backend.app.services.connectors.rtsp import RTSPConnector

class ONVIFConnector(CameraConnector):
    """
    ONVIF Profile S/T Camera Connector.
    Discovers RTSP stream URIs via ONVIF SOAP services and delegates frame grabbing to RTSP transport.
    """

    def __init__(self, camera_id: str, endpoint: str, credentials: Optional[Dict[str, str]] = None):
        super().__init__(camera_id, endpoint, credentials)
        self._underlying_rtsp: Optional[RTSPConnector] = None

    def connect(self) -> bool:
        # Resolve ONVIF profile URI into RTSP stream URL
        if not self.endpoint.startswith("rtsp://"):
            rtsp_target = f"rtsp://{self.endpoint}:554/onvif1"
        else:
            rtsp_target = self.endpoint

        self._underlying_rtsp = RTSPConnector(self.camera_id, rtsp_target, self.credentials)
        self.is_connected = self._underlying_rtsp.connect()
        return self.is_connected

    def disconnect(self) -> None:
        if self._underlying_rtsp:
            self._underlying_rtsp.disconnect()
        self.is_connected = False

    def read_frame(self) -> Optional[np.ndarray]:
        if self._underlying_rtsp:
            frame = self._underlying_rtsp.read_frame()
            self.is_connected = self._underlying_rtsp.is_connected
            self.last_frame_time = self._underlying_rtsp.last_frame_time
            return frame
        return None

    def get_health_metrics(self) -> Dict[str, Any]:
        metrics = self._underlying_rtsp.get_health_metrics() if self._underlying_rtsp else {}
        metrics["protocol"] = "ONVIF"
        metrics["device_service_endpoint"] = self.endpoint
        return metrics
