import os
from dataclasses import dataclass
from typing import Optional, Tuple, Any
import numpy as np
from backend.app.core.config import settings

@dataclass
class PlateCropResult:
    crop: Optional[np.ndarray]
    bbox: list[int]  # [x1, y1, x2, y2] relative to vehicle crop
    confidence: float
    detection_method: str  # NEURAL_YOLO_PLATE | MORPHOLOGICAL_CONTOUR | HEURISTIC_FALLBACK

class DedicatedPlateDetector:
    """
    Stage 2 Dedicated License Plate Detector.
    Isolates the exact high-contrast rectangular license plate boundary from a vehicle crop.
    Replaces naive static bottom-crop heuristics with neural detection + morphological fallback.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.GIVIN_PLATE_MODEL
        self._plate_model = None
        self._load_attempted = False

    def _load_model(self):
        if self._load_attempted:
            return
        self._load_attempted = True
        if self.model_path and os.path.exists(self.model_path):
            try:
                from ultralytics import YOLO
                self._plate_model = YOLO(self.model_path)
            except Exception:
                self._plate_model = None

    def detect_plate(self, vehicle_crop: np.ndarray) -> PlateCropResult:
        """
        Locates the exact license plate inside a cropped vehicle bounding box.
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            return PlateCropResult(crop=None, bbox=[0, 0, 0, 0], confidence=0.0, detection_method="EMPTY")

        vh, vw = vehicle_crop.shape[:2]
        self._load_model()

        # Path 1: Neural Dedicated Plate Detector (YOLO Plate Model)
        if self._plate_model is not None:
            try:
                results = self._plate_model(vehicle_crop, verbose=False)
                for res in results:
                    boxes = getattr(res, "boxes", None)
                    if boxes and len(boxes) > 0:
                        # Pick highest confidence plate detection
                        best_box = max(boxes, key=lambda b: float(b.conf[0]) if b.conf is not None else 0.0)
                        conf = float(best_box.conf[0])
                        x1, y1, x2, y2 = map(int, best_box.xyxy[0].tolist())
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(vw, x2), min(vh, y2)
                        plate_crop = vehicle_crop[y1:y2, x1:x2]
                        if plate_crop.size > 0:
                            return PlateCropResult(
                                crop=plate_crop,
                                bbox=[x1, y1, x2, y2],
                                confidence=round(conf, 3),
                                detection_method="NEURAL_YOLO_PLATE"
                            )
            except Exception:
                pass

        # Path 2: Morphological Aspect-Ratio & Sobel Gradient Plate Localization
        try:
            import cv2
            gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
            # Focus on lower 65% of vehicle where plates are mounted (front/rear bumper)
            roi_y_start = int(vh * 0.35)
            gray_roi = gray[roi_y_start:, :]
            
            # Vertical Sobel gradient to capture strong vertical plate character strokes
            grad_x = cv2.Sobel(gray_roi, cv2.CV_16S, 1, 0, ksize=3)
            abs_grad_x = cv2.convertScaleAbs(grad_x)
            
            # Low-pass filter and morphological closing with rectangular horizontal kernel
            blurred = cv2.GaussianBlur(abs_grad_x, (5, 5), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            best_contour = None
            best_aspect_score = 0.0
            best_bbox = None

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if h == 0 or w == 0:
                    continue
                aspect = float(w) / float(h)
                area = w * h
                total_roi_area = gray_roi.shape[0] * gray_roi.shape[1]
                
                # Standard Indian HSRP plate aspect ratio is ~3.5 to 5.0
                if 2.2 <= aspect <= 6.0 and (0.008 * total_roi_area) <= area <= (0.25 * total_roi_area):
                    score = 1.0 - abs(aspect - 4.2) / 4.2
                    if score > best_aspect_score:
                        best_aspect_score = score
                        # Map back to full vehicle crop coordinates
                        best_bbox = [x, y + roi_y_start, x + w, y + roi_y_start + h]

            if best_bbox:
                bx1, by1, bx2, by2 = best_bbox
                # Add 3px padding
                bx1, by1 = max(0, bx1 - 3), max(0, by1 - 3)
                bx2, by2 = min(vw, bx2 + 3), min(vh, by2 + 3)
                plate_crop = vehicle_crop[by1:by2, bx1:bx2]
                if plate_crop.size > 0:
                    return PlateCropResult(
                        crop=plate_crop,
                        bbox=[bx1, by1, bx2, by2],
                        confidence=round(0.85 + (best_aspect_score * 0.1), 3),
                        detection_method="MORPHOLOGICAL_CONTOUR"
                    )
        except Exception:
            pass

        # Path 3: Geometric Bumper Fallback Crop
        by1 = int(vh * 0.55)
        by2 = int(vh * 0.88)
        bx1 = int(vw * 0.20)
        bx2 = int(vw * 0.80)
        fallback_crop = vehicle_crop[by1:by2, bx1:bx2]
        return PlateCropResult(
            crop=fallback_crop,
            bbox=[bx1, by1, bx2, by2],
            confidence=0.72,
            detection_method="HEURISTIC_FALLBACK"
        )

dedicated_plate_detector = DedicatedPlateDetector()
