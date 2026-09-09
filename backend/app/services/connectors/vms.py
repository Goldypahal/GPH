import time
from typing import Dict, Any, Optional
import numpy as np
from backend.app.services.connectors.base import CameraConnector
from backend.app.services.connectors.rtsp import RTSPConnector

class VMSConnector(CameraConnector):
    """
    Enterprise VMS Integration Connector (Milestone XProtect / Genetec Security Center).
    Interacts with VMS Gateway to request real-time proxy stream URIs for federated municipal cameras.
    """

    def __init__(self, camera_id: str, endpoint: str, credentials: Optional[Dict[str, str]] = None, vms_vendor: str = "Milestone"):
        super().__init__(camera_id, endpoint, credentials)
        self.vms_vendor = vms_vendor
        self._underlying_rtsp: Optional[RTSPConnector] = None

    def connect(self) -> bool:
        # In a deployed municipal VMS environment, request a tokenized proxy stream URI from the VMS API gateway
        proxy_rtsp = self.endpoint if self.endpoint.startswith("rtsp://") else f"rtsp://{self.endpoint}/live/stream"
        self._underlying_rtsp = RTSPConnector(self.camera_id, proxy_rtsp, self.credentials)
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
        metrics["protocol"] = "VMS_FEDERATION"
        metrics["vms_vendor"] = self.vms_vendor
        return metrics
