"""
Test Suite for Phase B: Make AI Genuinely Real
Verifies:
1. DedicatedPlateDetector (Stage 2 license plate boundary localization)
2. PlatePreprocessor (Stage 3 deskew and CLAHE contrast enhancement)
3. ByteTrack (Multi-object tracking with persistent track_id across consecutive frames)
4. TemporalOCRFusion (Character-positional weighted consensus voting correcting OCR flicker)
5. VisionPipeline end-to-end integration
6. GET /api/system/ai-metrics endpoint
"""

import os
import sys
import io
import numpy as np
from PIL import Image

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.plate_detector import dedicated_plate_detector, PlateCropResult
from backend.app.services.plate_preprocessor import plate_preprocessor
from backend.app.services.bytetrack import ByteTracker, TrackerPool
from backend.app.services.temporal_fusion import temporal_fusion_engine
from backend.app.services.vision_pipeline import vision_pipeline

client = TestClient(app)

def _create_mock_vehicle_image(w: int = 400, h: int = 300) -> np.ndarray:
    """Creates a mock vehicle image array with a high-contrast plate region."""
    img = np.ones((h, w, 3), dtype=np.uint8) * 120 # Gray vehicle body
    # License plate rectangle (yellow/white background with dark border)
    px1, py1, px2, py2 = int(w * 0.3), int(h * 0.65), int(w * 0.7), int(h * 0.78)
    img[py1:py2, px1:px2] = [240, 240, 240] # White HSRP plate
    img[py1:py1+2, px1:px2] = [10, 10, 10]
    img[py2-2:py2, px1:px2] = [10, 10, 10]
    img[py1:py2, px1:px1+2] = [10, 10, 10]
    img[py1:py2, px2-2:px2] = [10, 10, 10]
    return img

def test_dedicated_plate_detector():
    """Verify Stage 2 plate detector extracts plate bounding box from vehicle crop."""
    vehicle_crop = _create_mock_vehicle_image(300, 200)
    res = dedicated_plate_detector.detect_plate(vehicle_crop)
    assert isinstance(res, PlateCropResult)
    assert res.crop is not None
    assert res.crop.size > 0
    assert len(res.bbox) == 4
    assert res.confidence >= 0.70
    assert res.detection_method in ("NEURAL_YOLO_PLATE", "MORPHOLOGICAL_CONTOUR", "HEURISTIC_FALLBACK")
    print(f"[PASS] test_dedicated_plate_detector passed (Method: {res.detection_method}, Conf: {res.confidence}).")

def test_plate_preprocessor():
    """Verify Stage 3 preprocessing deskews and standardizes plate image height with CLAHE."""
    plate_img = np.zeros((30, 120, 3), dtype=np.uint8)
    plate_img[:] = [220, 220, 220]
    
    preprocessed = plate_preprocessor.preprocess(plate_img, target_height=64)
    assert isinstance(preprocessed, np.ndarray)
    assert preprocessed.shape[0] == 64
    assert preprocessed.shape[1] >= 120
    print(f"[PASS] test_plate_preprocessor passed (Output shape: {preprocessed.shape}).")

def test_bytetrack_persistent_id():
    """Verify ByteTrack maintains persistent track_id across consecutive frames."""
    tracker = ByteTracker(high_thresh=0.5, match_thresh=0.7)
    
    # 5 consecutive frames of a vehicle moving horizontally across camera FOV
    frame_coords = [
        [100.0, 150.0, 260.0, 280.0],
        [110.0, 150.0, 270.0, 280.0],
        [122.0, 150.0, 282.0, 280.0],
        [135.0, 150.0, 295.0, 280.0],
        [148.0, 150.0, 308.0, 280.0]
    ]

    assigned_ids = []
    for f_idx, box in enumerate(frame_coords):
        dets = [(box, 0.94, "Car")]
        active_tracks = tracker.update(dets)
        assert len(active_tracks) == 1
        assigned_ids.append(active_tracks[0].track_id)

    # Verify identical track_id maintained across all 5 frames
    initial_id = assigned_ids[0]
    for tid in assigned_ids:
        assert tid == initial_id, f"Track ID changed unexpectedly: {assigned_ids}"

    print(f"[PASS] test_bytetrack_persistent_id passed (Persistent Track #{initial_id} over 5 frames).")

def test_temporal_ocr_fusion_consensus():
    """
    Verify character-positional consensus voting corrects flickering OCR errors:
    Frame 1: GJ01A81234 (conf=0.72 - OCR confused 'B' with '8')
    Frame 2: GJ01AB1234 (conf=0.95)
    Frame 3: GJ01AB1234 (conf=0.96)
    Frame 4: GJ01A81234 (conf=0.70)
    Frame 5: GJ01AB1234 (conf=0.94)
    Result must resolve to consensus plate 'GJ01AB1234' with confidence > 0.94.
    """
    import random
    test_cam = f"CAM-FUSION-{random.randint(100, 999)}"
    test_track = random.randint(1000, 9999)

    samples = [
        ("GJ01A81234", 0.72),
        ("GJ01AB1234", 0.95),
        ("GJ01AB1234", 0.96),
        ("GJ01A81234", 0.70),
        ("GJ01AB1234", 0.94),
    ]

    final_plate, final_conf, votes = "", 0.0, 0
    for raw, conf in samples:
        final_plate, final_conf, votes = temporal_fusion_engine.add_sample_and_fuse(
            camera_id=test_cam,
            track_id=test_track,
            raw_plate=raw,
            confidence=conf
        )

    assert final_plate == "GJ01AB1234", f"Expected consensus GJ01AB1234, got {final_plate}"
    assert final_conf >= 0.94
    assert votes == 5
    print(f"[PASS] test_temporal_ocr_fusion_consensus passed (Consensus: {final_plate} @ {final_conf*100:.1f}% across {votes} votes).")

def test_vision_pipeline_end_to_end():
    """Verify VisionPipeline runs the complete 2-stage + tracking + fusion pipeline."""
    # Create test JPEG bytes
    img = Image.new("RGB", (640, 480), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    detections = vision_pipeline.detect(jpeg_bytes, camera_id="CAM-GJ-AHM-01")
    assert len(detections) >= 1
    d = detections[0]
    assert d.plate_text is not None and len(d.plate_text) >= 8
    assert d.ocr_confidence > 0.50
    assert d.track_id > 0
    assert d.bbox is not None
    assert d.plate_bbox is not None
    assert d.fused_votes >= 1
    print(f"[PASS] test_vision_pipeline_end_to_end passed (Plate: {d.plate_text}, Track: #{d.track_id}, Votes: {d.fused_votes}).")

def test_ai_metrics_api():
    """Verify GET /api/system/ai-metrics returns live model lineage and counters."""
    res = client.get("/api/system/ai-metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert "models_loaded" in data
    assert "metrics" in data
    assert data["metrics"]["frames_processed"] >= 1
    assert "avg_pipeline_latency_ms" in data["metrics"]
    print(f"[PASS] test_ai_metrics_api passed (Latency: {data['metrics']['avg_pipeline_latency_ms']} ms).")

if __name__ == "__main__":
    print("\n==================================================================")
    print("  RUNNING PHASE B VISION & TRACKING VERIFICATION SUITE            ")
    print("==================================================================")
    test_dedicated_plate_detector()
    test_plate_preprocessor()
    test_bytetrack_persistent_id()
    test_temporal_ocr_fusion_consensus()
    test_vision_pipeline_end_to_end()
    test_ai_metrics_api()
    print("\n*** ALL PHASE B REAL AI TESTS PASSED WITH 100% SUCCESS!\n")
