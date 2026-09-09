"""Real vision pipeline adapters for GIVIN.

Uses YOLO for vehicle detection and PaddleOCR for OCR when the optional
production dependencies/models are installed. Simulation is explicit and
never silently used when real mode is requested.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, asdict
from typing import Any, Optional
import numpy as np
from backend.app.services.anpr_engine import ANPREngine

@dataclass
class PlateDetection:
    plate_text: str
    ocr_confidence: float
    bbox: Optional[list[float]] = None
    detector_confidence: float = 0.0
    vehicle_type: str = "Unknown"
    vehicle_color: str = "Unknown"
    source: str = "real"
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class VisionPipelineError(RuntimeError):
    pass

class VisionPipeline:
    """Lazy-loaded YOLO + PaddleOCR pipeline.

    GIVIN_VISION_MODE=real|auto|simulation (default auto)
    GIVIN_YOLO_MODEL=path/to/model.pt
    """
    def __init__(self) -> None:
        self.mode = os.getenv("GIVIN_VISION_MODE", "auto").lower()
        self.yolo_model_path = os.getenv("GIVIN_YOLO_MODEL", "")
        self._detector = None
        self._ocr = None
        self._load_error: Optional[str] = None

    def _load_models(self) -> None:
        if self._detector is not None and self._ocr is not None:
            return
        try:
            from ultralytics import YOLO  # type: ignore
            from paddleocr import PaddleOCR  # type: ignore
            self._detector = YOLO(self.yolo_model_path or "yolo11n.pt")
            self._ocr = PaddleOCR(use_doc_orientation_classify=False,
                                  use_doc_unwarping=False,
                                  use_textline_orientation=False,
                                  lang="en")
        except Exception as exc:
            self._load_error = str(exc)

    @staticmethod
    def _decode_image(contents: bytes) -> np.ndarray:
        try:
            import cv2  # type: ignore
        except ImportError as exc:
            raise VisionPipelineError("opencv-python-headless is required for real vision mode") from exc
        frame = cv2.imdecode(np.frombuffer(contents, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise VisionPipelineError("Unsupported or corrupt image")
        return frame

    @staticmethod
    def _preprocess_plate(crop: np.ndarray) -> np.ndarray:
        import cv2  # type: ignore
        if crop.size == 0:
            return crop
        scale = 3 if max(crop.shape[:2]) < 600 else 2
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        return cv2.detailEnhance(crop, sigma_s=10, sigma_r=0.15)

    def _ocr_plate(self, crop: np.ndarray) -> tuple[str, float]:
        if self._ocr is None:
            raise VisionPipelineError(f"PaddleOCR unavailable: {self._load_error or 'model not loaded'}")
        result = self._ocr.predict(self._preprocess_plate(crop))
        texts, scores = [], []
        for page in result or []:
            data = getattr(page, "json", None)
            data = data() if callable(data) else data
            if not isinstance(data, dict):
                continue
            payload = data.get("res", data)
            texts.extend(str(x) for x in payload.get("rec_texts", []))
            scores.extend(float(x) for x in payload.get("rec_scores", []))
        raw = re.sub(r"[^A-Za-z0-9]", "", "".join(texts)).upper()
        return raw, (sum(scores) / len(scores) if scores else 0.0)

    def detect(self, contents: bytes) -> list[PlateDetection]:
        if self.mode == "simulation":
            return []
        self._load_models()
        if self._detector is None or self._ocr is None:
            raise VisionPipelineError(
                "Real vision models are unavailable. Install vision dependencies and configure "
                "GIVIN_YOLO_MODEL, or explicitly set GIVIN_VISION_MODE=simulation."
            )
        frame = self._decode_image(contents)
        results = self._detector(frame, verbose=False)
        detections: list[PlateDetection] = []
        vehicle_labels = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                cls = int(box.cls[0]) if box.cls is not None else -1
                if cls not in vehicle_labels:
                    continue
                coords = [float(x) for x in box.xyxy[0].tolist()]
                x1, y1, x2, y2 = map(int, coords)
                crop = frame[max(0,y1):max(y1+1,y2), max(0,x1):max(x1+1,x2)]
                if crop.size == 0:
                    continue
                raw, ocr_conf = self._ocr_plate(crop[int(crop.shape[0]*0.45):])
                corrected, format_conf, valid = ANPREngine.validate_and_correct(raw)
                if not corrected:
                    continue
                detections.append(PlateDetection(
                    plate_text=corrected,
                    ocr_confidence=min(0.99, ocr_conf*0.7 + format_conf*0.3),
                    bbox=coords,
                    detector_confidence=float(box.conf[0]) if box.conf is not None else 0.0,
                    vehicle_type=vehicle_labels[cls],
                    source="yolo+paddleocr",
                ))
        return detections

vision_pipeline = VisionPipeline()
