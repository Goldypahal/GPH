# Low-Level Design (LLD) Document
## Gujarat Integrated Video Intelligence Network (GIVIN)
**Document Classification:** Confidential / Law Enforcement Technical Specification  
**Version:** 1.2  
**Target Environment:** Gujarat State Data Centre (GSDC) / Police Netram C4I  

---

## 1. System Overview & Architectural Boundaries

The **Gujarat Integrated Video Intelligence Network (GIVIN)** provides an enterprise-grade, statewide video ingestion, AI analytics, and spatiotemporal tracking platform across 26 independent government departments.

```
+---------------------------------------------------------------------------------------------------+
|                                 GIVIN LOW-LEVEL COMPONENT PIPELINE                                |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [CAMERA CONNECTOR ENGINE]                                                                        |
|  - RTSP / RTSPS / HTTP Connector Factory (Threaded Ingest, Frame Sampler)                         |
|  - 7-Stage Lifecycle: REGISTER -> VALIDATE -> CONNECT -> AUTH -> HEALTH -> STREAM -> AI_ENABLED   |
|                                     |                                                             |
|                                     v                                                             |
|  [AI VISION & ANPR PIPELINE]                                                                      |
|  - Object Detector (YOLOv8 / MobileNet) -> Classify: Car, Truck, Bus, Motorcycle, Auto           |
|  - ByteTrack Local Motion Tracker -> Stable Track IDs within Camera Field of View                 |
|  - Plate Detector (HSRP Bounding Box) -> CLAHE Preprocessing & Bilateral Deskewing                |
|  - OCR Engine (Tesseract / PaddleOCR / Regex Filter) -> Multi-Frame Temporal Confidence Fusion    |
|                                     |                                                             |
|                                     v                                                             |
|  [EVENT STREAMING & DISPATCH BACKBONE]                                                            |
|  - Kafka / KRaft Topics: givin.sightings.raw, givin.sightings.normalized, givin.alerts.triggered    |
|  - In-Process Dual-Mode EventBus with MicroBatchIngestionWorker & DLQ Quarantine / Replay         |
|                                     |                                                             |
|                                     v                                                             |
|  [INTELLIGENCE & CORRELATION ENGINE]                                                              |
|  - Watchlist Matcher (Thread-Safe TTL Cache, Plate Normalization, Disambiguation Regex)           |
|  - Cross-Camera Graph Correlation (Adjacency Matrix, Spatiotemporal Route Reconstruction)         |
|  - Live Pursuit Dead-Reckoning (Heading Cone, Speed Projection, Next Camera Reconfirmation)       |
|  - Impossible Speed & Cloned Plate Anomaly Detector (>180 km/h configurable)                     |
|                                     |                                                             |
|                                     v                                                             |
|  [GOVERNMENT ADAPTER LAYER]                                                                       |
|  - VAHAN 4.0 (Stolen vehicle status, RC details, chassis lookup)                                  |
|  - SARTHI (Driver license validity, disqualification status)                                      |
|  - eGujCop / CCTNS (Criminal history, FIR records, lookout notices)                               |
|  - AFIS / NAFIS (Biometric fingerprint & facial hotlist matching)                                 |
|  - Multi-Mode Gates: MOCK / SANDBOX / AUTHORIZED_PRODUCTION (mTLS, GSWAN VPN)                     |
|                                     |                                                             |
|                                     v                                                             |
|  [EVIDENCE VAULT & LEGAL CHAIN OF CUSTODY]                                                        |
|  - WORM Storage Driver (Local WORM / MinIO Object Lock Compliance Retention)                      |
|  - SHA-256 Byte-Level Integrity Seals & HMAC-SHA256 Signatures                                    |
|  - Append-Only Custody Log (VIEW, EXPORT, COURT_SUBMIT)                                           |
|  - Section 65B Indian Evidence Act / Section 63 BSA 2023 Statutory Export Bundle                  |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Camera Lifecycle & Connector State Machine

### 2.1 State Transitions
The camera lifecycle transitions through 7 distinct deterministic states:
1. `REGISTERED`: Camera metadata (logical ID, department, district, location, GPS, protocol) created in SQL catalog.
2. `VALIDATING`: Protocol and syntax validation (URI format, IP range check, district boundaries).
3. `CONNECTING`: Network transport probing — DNS resolution, TCP handshake to host/port.
4. `AUTHENTICATING`: RTSP `OPTIONS` / `DESCRIBE` handshake with digest/basic authentication credentials.
5. `HEALTH_CHECKED`: Validates transport responsiveness, latency measurement, and stream reachability.
6. `STREAMING`: Frame ingestion active via OpenCV / GStreamer / MJPEG pipeline; records FPS and frame timestamp.
7. `AI_ENABLED`: Camera actively bound to AI vision worker queues for vehicle detection and ANPR.

### 2.2 Telemetry Provenance Standards
Telemetry produced by camera connectors follows strict provenance definitions:
- `MEASURED`: Physical TCP socket round-trip time (`latency_ms`), active frame count, FPS.
- `DERIVED`: Stream uptime derived from `first_frame_timestamp` and `last_frame_timestamp`.
- `UNAVAILABLE_AT_APPLICATION_LAYER`: Transport packet loss (requires RTCP or SNMP router counters; never hardcoded).

---

## 3. Computer Vision & ANPR Processing Pipeline

### 3.1 Pipeline Stages
```
[Video Frame] 
      │
      ▼
[1. Object Detector] ─────────► Bounding Box [x1, y1, x2, y2], Class, Confidence
      │
      ▼
[2. ByteTrack Tracker] ───────► Track ID assignment (Association via IoU & Kalman Filter)
      │
      ▼
[3. Plate Detector] ──────────► Sub-crop: High-Security Registration Plate (HSRP)
      │
      ▼
[4. Plate Preprocessing] ─────► Grayscale -> CLAHE (Contrast Limiting) -> Bilateral Filter -> Deskew
      │
      ▼
[5. OCR Engine] ──────────────► Raw alphanumeric string + character-level confidence
      │
      ▼
[6. Normalizer & Disambiguator]► Regex filter (e.g. ^GJ[0-9]{2}[A-Z]{1,3}[0-9]{4}$), '8'<->'B', '0'<->'O'
      │
      ▼
[7. Multi-Frame Fusion] ──────► Temporal voting window (Consensus across >= 3 frames)
      │
      ▼
[Normalized Vehicle Sighting]
```

### 3.2 Provenance & Hardware Introspection
- Device Backend: `CUDA` (if GPU available), `TensorRT` (edge gateways), or `CPU` fallback.
- In unmeasured states (0 frames processed), telemetry returns `latency_p50_ms: null` with `latency_provenance: "UNAVAILABLE"`.

---

## 4. Spatiotemporal & Cross-Camera Intelligence

### 4.1 Trajectory Reconstruction
Given a target license plate, `VehicleTracker.reconstruct_journey(db, plate)`:
1. Queries chronologically ordered `VehicleSighting` records.
2. Calculates Haversine distance between consecutive camera coordinates:
   Distance formula with Earth radius R = 6371.0 km.
3. Computes inter-camera velocity:
   v = distance / time_delta (km/h)
4. Detects Physical Anomalies:
   - If v > IMPOSSIBLE_SPEED_THRESHOLD_KMH (default 180.0 km/h), marks segment as IMPOSSIBLE_SPEED and flags potential cloned registration plates.
   - If v > SUSPICIOUS_SPEED_THRESHOLD_KMH (default 130.0 km/h), marks segment as SUSPICIOUS_SPEED.

### 4.2 Live Pursuit Dead-Reckoning
When live pursuit is triggered:
- Takes the vehicle's last two verified camera sightings.
- Computes bearing / compass heading and velocity.
- Dead-reckons real-time position along the trajectory:
  delta_d = v * delta_t_elapsed
- Predicts next downstream camera intercepting the heading cone within a configurable sector angle (+/- 35 deg).

---

## 5. Event Streaming & Micro-Batching Architecture

### 5.1 Kafka Topics & Canonical Data Models
1. `givin.sightings.raw`: Unprocessed sightings containing camera ID, timestamp, raw image reference, detector boxes.
2. `givin.sightings.normalized`: Cleaned, validated plates with temporal consensus confidence scores.
3. `givin.alerts.triggered`: Watchlist matches with assigned severity, officer dispatch status, and audit metadata.
4. `givin.telemetry.camera`: Camera heartbeat, network latency, decode failures, and FPS.
5. `givin.dlq`: Malformed, unparseable, or failed ingestion payloads quarantined for manual inspection.

### 5.2 Micro-Batching & DLQ Replay
- `MicroBatchIngestionWorker`: Accumulates sightings into micro-batches of up to 500 items or 50ms flush timeout, performing bulk SQL inserts.
- `DeadLetterQueueManager`: Thread-safe (`threading.RLock`) poison pill isolation. Prevents poison pills from blocking the primary ingestion queue.
- Replay API (`POST /api/system/dlq/replay`): Safely reprocesses quarantined events upon schema fix.

---

## 6. Government Adapters & Integration Architecture

### 6.1 State Machine & Operational Modes
Each adapter (`VAHAN`, `SARTHI`, `eGujCop`, `AFIS/NAFIS`) implements `BaseGovAdapter`:
- `MOCK`: In-memory deterministic fixture dataset for unit tests and local sandboxing.
- `SANDBOX`: Connects to government pre-production staging gateways.
- `AUTHORIZED_PRODUCTION`: Requires active GSWAN VPN route, valid x509 client certificate, mTLS handshake, and authorized API key.

### 6.2 Truthful Connection States
Adapters independently report:
- `NOT_CONFIGURED`: Missing endpoint or credential.
- `CONFIGURED`: Credentials present, awaiting live handshake.
- `CONNECTED`: TCP socket established to gateway.
- `AUTHENTICATED`: mTLS / token validation successful.
- `AUTHORIZED`: Department permissions verified.
- `EXTERNAL_DEPENDENCY`: Gateway offline or unreachable via GSWAN.

---

## 7. Evidence Vault, WORM & Section 65B Compliance

### 7.1 WORM (Write-Once-Read-Many) Storage
- Storage backend: Local WORM Driver (`backend/app/services/storage/local_storage.py`) or MinIO S3 Object Lock Compliance Mode (`backend/app/services/storage/minio_storage.py`).
- Immutability Enforcement:
  - Overwrite attempts (`PUT` existing key): Rejection with `HTTP 409 Conflict`.
  - Delete attempts (`DELETE` key): Rejection with `HTTP 403 Forbidden`.

### 7.2 Cryptographic Integrity Records
- Byte-level SHA-256 hash computed over exact raw evidence bytes (JPEG crop, full frame, dossier).
- HMAC-SHA256 digital seal incorporates camera ID, timestamp, plate, snapshot hash, and officer ID.
- Append-only audit custody ledger tracks every access, export, or status change.

### 7.3 Section 65B IEA / Section 63 BSA Legal Standard
All exported evidence bundles include:
- `manifest.json`: Cryptographic index of all files and checksums.
- `Section_65B_Certificate.json`: Device operational state declaration, certifying officer, and statutory legal disclaimer.
- `investigation_dossier.json`: Complete spatiotemporal trajectory, sightings timeline, and cross-camera travel analysis.

---

## 8. Enterprise Security & OIDC / ABAC Specification

### 8.1 Authentication & Token Verification
- Production Mode (`ENVIRONMENT=production`):
  - Strictly requires `Authorization: Bearer <JWT>`.
  - Cryptographic RS256/ES256 signature verification against Keycloak / Gujarat SSO JWKS endpoint.
  - Strict validation of `iss`, `aud`, `exp`, `nbf`, and `sub`.
  - Zero development bypass or default super-admin identities.
- Non-Production Mode (`ENVIRONMENT!=production`):
  - Anonymous requests without header rejected with `401 Unauthorized`.
  - Explicit header `X-Dev-Bypass-Token` creates a sandboxed standard officer identity (`OFFICER`, `PRIMARY_INVESTIGATOR`), never `SUPER_ADMIN`.

### 8.2 Attribute-Based Access Control (ABAC)
Policy evaluated across 4 orthogonal dimensions:
1. Clearance Level: `TOP_SECRET` > `SECRET` > `CONFIDENTIAL` > `UNCLASSIFIED`.
2. Department Isolation: `HOME_POLICE` has statewide supervision; other departments restricted to their own cameras/sightings unless an active federation request is approved.
3. District Fencing: Officers restricted to their assigned jurisdiction (e.g. `Ahmedabad`, `Surat`) unless holding `Statewide` clearance.
4. Role Permissions: 5-tier role hierarchy (`SUPER_ADMIN`, `DISTRICT_SP`, `POLICE_INSPECTOR`, `OPERATOR`, `AUDITOR`).

---

## 9. Sentinel Camera Grid Integration Architecture (Contract Section 39)

### 9.1 Camera Catalogue Contract (`GET /api/ingest`)
- Upstream Discovery: Discovers cameras dynamically from the upstream Sentinel Gateway or persistent GIVIN registry.
- Zero Hard-coding: Never fabricates camera entries; returns structured error if catalogue is unreachable.
- Standardized Metadata: Each camera record normalizes `camera_id`, `name`, `location`, `district`, `live_status`, `codec`, `resolution`, `declared_fps`, `bitrate_kbps`, `rtsp_url`, and `stream_properties` (`forced_transport: TCP`, `supports_pts: true`, `variable_fps_tolerant: true`).
- Automatic Lifecycle Sync: Discovered cameras automatically register into the persistent GIVIN database.

### 9.2 Forced TCP Transport
- OpenCV FFMPEG transport strictly forced via `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp`.
- Silent UDP fallbacks strictly prohibited to prevent packet loss, frame dropping, and macroblocking on Gujarat police WAN.

### 9.3 Authoritative PTS Timing Engine
- Media Clock: Presentation Timestamp (PTS) from the container/codec stream serves as the single source of truth for media time.
- Field Propagation: Downstream tracking and kinematics receive `SentinelFrameMeta` carrying `frame_pts`, `pts_delta`, `arrival_timestamp`, and `camera_id`.
- Velocity Calculation: Target displacement is strictly normalized by `pts_delta` (`displacement / pts_delta`), completely decoupling kinematics from network arrival jitter.
- Prohibition of CAP_PROP_FPS: Hardware FPS declarations are never used to synthesize inter-frame time deltas.

### 9.4 Variable Frame Rate (VFR) & GOP Burst Resilience
- Variable inter-frame gaps (10ms to 500ms) handled smoothly without frame drops or pipeline stalls.
- GOP Join Bursts: Rapid delivery of buffered keyframes upon RTSP connection (`arrival_interval < 0.35 * pts_delta` within first 2.5s) tagged as `is_burst_frame=True`. Kinematics maintain correct velocities without triggering false 800+ km/h alerts.
- Recoverable Decoder Warnings: Non-fatal join warnings (h264 sps/pps sync, decode_slice_header errors) logged to telemetry without tearing down capture instances.

### 9.5 Exponential Backoff Reconnection Engine
- Jittered exponential backoff: Initial retry 2.0s, doubling on consecutive disconnects up to a ceiling of 30.0s.
- Automatic Reset: Backoff delay resets to 2.0s immediately upon successful stream re-acquisition and frame delivery.
- Observability: Reconnect attempts, failures, and disconnect timestamps tracked in `CameraStreamTelemetry`.

### 9.6 Heterogeneous Codec & Resolution Handling
- Codec Support: Dual-stack support for H.264 (AVC) and H.265 (HEVC).
- Explicit Codec Guard: Unsupported formats (e.g. VP9, MPEG-2) transition stream state to `UNSUPPORTED_CODEC` without crashing the gateway.
- Resolution Invariance: Native sensor resolutions (e.g., 4K, 1080p, 720p) preserved in metadata while frames scale uniformly to YOLOv8 inference resolution (640x640) with coordinate rescaling factors.

### 9.7 Scene Loop Discontinuity Detection & Recovery
- Cut Detection: Sudden backward jumps in PTS (`pts < last_pts`) or severe temporal gaps (> 5.0s) identified as scene cuts or video loop resets.
- Tracker Reset: ByteTracker invalidates tracked and lost pools via `self.reset()`, guaranteeing tracks do not span across loop boundaries.
- Journey Reconstruction: Negative time differences (`time_diff < 0`) in trajectory analysis flagged as `SCENE_DISCONTINUITY_RESET` rather than false impossible-speed violations.

### 9.8 Consume-Only Gateway Contract & Load Pacing
- Consume-Only: GIVIN operates strictly as a consumer; exposes no endpoints or methods for stream publication or gateway camera mutation.
- Load Pacing: Stream concurrency bounded by `MAX_ACTIVE_CAMERA_STREAMS` (default 32) and `MAX_CONNECT_CONCURRENCY` (default 4). Exceeding requests rejected with `LOAD_PACING_EXCEEDED`.

### 9.9 Stream Health Truth State Machine
Maintains 8 distinct, un-collapsed states for full operational transparency:
1. `CATALOGUE_LIVE`: Camera entry discovered and validated in catalogue.
2. `TCP_REACHABLE`: TCP socket handshake established on port 554/8554.
3. `RTSP_CONNECTED`: RTSP DESCRIBE/SETUP completed.
4. `RTSP_AUTHENTICATED`: Credentials accepted by camera endpoint.
5. `STREAM_ACTIVE`: Transport channel open and waiting for video frames.
6. `FRAME_RECEIVING`: Demuxer actively receiving raw video packets.
7. `FRAME_FRESH`: Decoded frames arriving within freshness threshold (< 5.0s).
8. `AI_PROCESSING`: Ingested frame successfully processed by YOLOv8 ANPR inference.

### 9.10 Sentinel Deployment Readiness Endpoint
`GET /api/system/sentinel-readiness` provides pre-flight readiness verification across 9 automated checks:
- `camera_catalogue`, `rtsp_tcp`, `pts_timing`, `reconnect`, `h264`, `h265`, `mixed_resolution`, `scene_discontinuity`, `load_pacing`.
