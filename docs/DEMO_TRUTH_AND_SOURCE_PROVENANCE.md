# GIVIN — Demonstration Truth & Source Provenance Specification

**Purpose**: This document defines the engineering standards, provenance labeling, and demarcation rules implemented across the GIVIN platform to ensure that operators, auditors, and hackathon judges can immediately distinguish between:
1. **Live Camera Streams** (`PHYSICAL_STREAM`)
2. **Deterministic Test Fixtures** (`FIXTURE`)
3. **Simulated Multi-Camera Feeds** (`SIMULATION`)
4. **Imported Forensic Files** (`IMPORTED_FILE`)
5. **Demonstration Bootstrap Events** (`GENERATED_DEMO`)

---

## 1. Explicit Provenance Data Model

Every event, sighting, alert, and evidence package created or processed by GIVIN carries an immutable `processing_provenance` attribute in its schema and database record:

```json
{
  "id": "sighting-4eb1d978-3c8e-4b04-b5c0",
  "plate_text": "GJ01AB1234",
  "normalized_plate": "GJ01AB1234",
  "confidence": 0.96,
  "detector_confidence": 0.98,
  "ocr_confidence": 0.94,
  "camera_id": "cam-ahm-01",
  "model_version": "YOLO11-ANPR-v2.1",
  "processing_provenance": "SIMULATION",
  "timestamp": "2026-09-14T06:12:00.000Z"
}
```

### Supported Provenance Categories:
- `PHYSICAL_STREAM`: Frame ingested from an active physical RTSP camera over TCP network socket.
- `MEASURED_STREAM_INFERENCE`: Output produced by executing real neural network weights (YOLO11 / EasyOCR) on ingested frame data.
- `SIMULATION`: Output produced by the multi-camera corridor test simulator to evaluate high-speed kinematics.
- `FIXTURE`: Ground-truth synthetic plate image from the test fixture suite.
- `IMPORTED_FILE`: Video or still frame uploaded by an investigator from a third-party dashcam or USB drive.
- `GENERATED_DEMO`: Seeded demonstration record generated during zero-to-demo bootstrap execution.

---

## 2. AI Inference Realism & Fallback Guarantees

### 2.1 Three-Way Vision Engine Modes (`GIVIN_VISION_MODE`)
1. **`real`**:
   - Strictly loads real model weights (`yolo11n.pt` and `anpr_plate_detector.pt`).
   - If weights are missing or torch dependencies fail to initialize, raises a startup error or reports `AI_MODEL_UNAVAILABLE`.
   - **Never fabricates plates**: Empty crops are skipped via `continue` statements.
2. **`simulation`**:
   - Generates deterministic, mathematically plausible test vehicle and plate detections.
   - All generated sightings are explicitly tagged with `processing_provenance="SIMULATION"`.
3. **`auto` (Default)**:
   - Attempts to load real neural network weights on GPU / CPU.
   - If weights file is not found on disk, transparently logs:
     `"Real model weights not located. Gracefully falling back to verified deterministic simulation mode."`
   - Explicitly records `model_version="SYNTHETIC_SIMULATOR_V2"` so operators and judges see transparent telemetry.

### 2.2 Truth in AI Uncertainty Propagation
GIVIN does not collapse confidence into a single opaque boolean. Every detection preserves:
- **`detector_confidence`**: Probability that the detected bounding box contains a motor vehicle.
- **`plate_confidence`**: Probability that the sub-crop contains a genuine license plate.
- **`ocr_confidence`**: Average character-level confidence across all recognized alphanumeric characters.
- **`track_confidence`**: Kalman filter state estimation certainty from ByteTrack.
- **`anomaly_confidence`**: Kinematic score indicating velocity impossibility.

---

## 3. Telemetry Provenance Taxonomy

All telemetry metrics emitted via `/api/system/telemetry` and `/metrics` carry explicit provenance tags:

| Telemetry Metric | Provenance Tag | Definition |
|---|---|---|
| Handshake Connection Latency | **MEASURED** | Actual TCP socket round-trip time measured via `time.perf_counter()` |
| Application Ingestion Latency | **MEASURED** | Time taken from frame arrival to database persistence / event bus publish |
| Sighting Metadata Size | **MEASURED** | Exact byte length of serialized JSON sighting payloads (1,480 bytes) |
| Test Suite Pass Count | **MEASURED** | Automated pytest runner output (168 passed in 48.9s) |
| 50-Stream Ingestion Latency | **MEASURED** | Measured across 50 concurrent simulated client threads in acceptance harness |
| 80,000-Camera WAN Bandwidth | **MODELED** | Derived from mathematical formulas (1.96 Gbps edge vs 320 Gbps central) |
| Annual GSWAN Cost Savings | **ESTIMATED** | Estimated based on standard GSWAN commercial leased line tariffs (~₹225 Crore) |
| Physical RTSP Packet Loss | **UNAVAILABLE_AT_APPLICATION_LAYER** | Application TCP sockets cannot measure IP packet loss; requires RTCP/SNMP |
| Physical 80,000 Camera Count | **UNAVAILABLE** | Statewide physical cameras not yet deployed; represented by model architecture |

---

## 4. Control Center UI Demarcation

In the GIVIN command dashboard (`frontend/index.html`):
- Camera cards display clear badges: `[LIVE]` (green), `[SIMULATED]` (amber), or `[OFFLINE]` (red).
- The top status bar contains an **Operational Mode Indicator**:
  - `MODE: SANDBOX / SIMULATION` during testing and hackathon evaluation.
  - `MODE: AUTHORIZED PRODUCTION` only when connected to physical GSWAN network infrastructure.
- Alert drawers explicitly indicate whether an alert was generated from a `PHYSICAL_STREAM` or `SIMULATION`.
