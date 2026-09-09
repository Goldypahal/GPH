from typing import Any, Optional, Dict
from backend.app.services.connectors.base import CameraConnector
from backend.app.services.connectors.rtsp import RTSPConnector
from backend.app.services.connectors.onvif import ONVIFConnector
from backend.app.services.connectors.vms import VMSConnector

class ConnectorFactory:
    """
    Factory creating appropriate protocol driver based on camera ORM registration.
    """

    @staticmethod
    def create_connector(camera: Any, credentials: Optional[Dict[str, str]] = None) -> CameraConnector:
        cam_id = getattr(camera, "logical_camera_id", getattr(camera, "id", "UNKNOWN_CAM"))
        protocol = getattr(camera, "protocol", "RTSP").upper()
        stream_url = getattr(camera, "stream_url", "") or f"rtsp://127.0.0.1:8554/{cam_id}"
        vms_type = getattr(camera, "vms_type", "Milestone")

        if protocol in ("ONVIF", "ONVIF_PROFILE_S"):
            return ONVIFConnector(camera_id=cam_id, endpoint=stream_url, credentials=credentials)
        elif protocol in ("VMS", "VMS_API", "VMS-API"):
            return VMSConnector(camera_id=cam_id, endpoint=stream_url, credentials=credentials, vms_vendor=vms_type)
        else: # Default RTSP / RTSPS
            return RTSPConnector(camera_id=cam_id, stream_url=stream_url, credentials=credentials)
