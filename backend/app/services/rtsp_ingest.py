import io
import time
import os
import threading
from typing import Generator, Optional, Callable, Dict, Any
from PIL import Image

class RTSPIngestService:
    """
    RTSP and Video File Frame Ingestion Service.
    Extracts frames at a controlled sample rate (2-5 FPS) to conserve
    bandwidth and compute while providing continuous video analytics.
    """

    def __init__(self, target_fps: float = 3.0):
        self.target_fps = target_fps
        self.interval = 1.0 / target_fps
        self._active_streams: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def sample_frames_from_source(
        self,
        source_uri: str,
        max_frames: Optional[int] = None
    ) -> Generator[bytes, None, None]:
        """
        Samples frames from an RTSP stream, local video file, or synthetic source.
        Yields JPEG byte buffers at target_fps.
        """
        # Check if source is a real video file or RTSP stream and cv2 is available
        cv2_available = False
        try:
            import cv2
            cv2_available = True
        except ImportError:
            pass

        if cv2_available and source_uri and (source_uri.startswith("rtsp://") or os.path.exists(source_uri)):
            cap = cv2.VideoCapture(source_uri)
            frames_yielded = 0
            last_sample_time = 0.0

            try:
                while cap.isOpened():
                    now = time.time()
                    ret, frame = cap.read()
                    if not ret:
                        # Loop video if file
                        if os.path.exists(source_uri):
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                        break

                    if (now - last_sample_time) >= self.interval:
                        last_sample_time = now
                        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        yield buffer.tobytes()
                        frames_yielded += 1
                        if max_frames and frames_yielded >= max_frames:
                            break
                    time.sleep(0.01)
            finally:
                cap.release()
        else:
            # Fallback high-performance synthetic frame generator simulating camera road view
            from backend.app.services.feed_connector import FeedConnector
            frame_idx = 0
            while True:
                frame_bytes = FeedConnector.generate_live_frame(
                    camera_id="INGEST-SOURCE",
                    camera_name="RTSP Highway Camera",
                    district="Gujarat",
                    frame_idx=frame_idx
                )
                yield frame_bytes
                frame_idx += 1
                if max_frames and frame_idx >= max_frames:
                    break
                time.sleep(self.interval)

rtsp_ingest_service = RTSPIngestService(target_fps=3.0)
