# High-Level Design (HLD) Document
## Gujarat Integrated Video Intelligence Network (GIVIN)
**Prepared for:** Gujarat Police Innovation Hackathon 2026  
**Document Classification:** Confidential / Law Enforcement Technical Proposal  
**Version:** 1.0  

---

## 1. System Context & Solution Model Justification

### 1.1 The Challenge
The Government of Gujarat seeks to integrate video feeds and metadata from approximately 80,000 cameras operated by 26 independent Government Departments into a single, cohesive command-and-control intelligence platform. The primary challenges are:
- **Heterogeneous Hardware & Protocols**: Incompatible camera hardware (Hikvision, Dahua, CP Plus, Axis, Honeywell, Hanwha), diverse VMS platforms (Milestone, Genetec, Qognify, Nx Witness, local NVRs), and varying protocols (RTSP, ONVIF, HTTP-FLV, proprietary SDKs).
- **Geographic Dispersion**: Camera deployments extending over 1,000 km across urban centers (Ahmedabad, Surat, Vadodara, Rajkot) and border districts (Valsad bordering Maharashtra, Dahod bordering Madhya Pradesh, and Bhuj/Kutch coastal and international borders).
- **Network Bandwidth Constraints**: Streaming 80,000 continuous full-HD video channels across the statewide WAN is technically impractical and financially unviable, demanding ~320 Gbps of uninterrupted uplink.
- **Law Enforcement Cross-Referencing**: The necessity to cross-reference live detections with critical state and national databases: **VAHAN** (vehicle registration), **SARTHI** (driver licensing), **eGujCop / CCTNS** (crime records), and **AFIS / NAFIS** (biometrics).

### 1.2 Winning Hybrid Architecture Rationale
GIVIN adopts a **Hybrid Architecture** combining:
- **Model 1 (Registry & GIS Foundation)**: Establishes a standardized spatial catalog of all camera assets, department ownership, and operating health.
- **Model 3 (VMS Federation & Middleware)**: Deploys protocol-agnostic connectors that interface with existing NVRs/VMS without replacing departmental equipment.
- **Selective Edge/Regional AI**: Ingests and processes video feeds at 33 District Edge Nodes, extracting structured metadata (vehicle type, color, plate OCR) and streaming compact JSON telemetry centrally (averaging 8 Kbps per camera). Full-resolution video is streamed to the Central Command Center on-demand only during active incidents or forensic reviews.
- **Model 2 (Unified Viewing & Analytics)**: Delivers a unified browser-based C4I dashboard with multi-grid live monitoring, GIS spatial visualization, and real-time alerts.

```
+---------------------------------------------------------------------------------------------------+
|                                 GIVIN 3-TIER SYSTEM TOPOLOGY                                      |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [TIER 1: 33 DISTRICT EDGE NODES & LOCAL CONNECTORS]                                              |
|  +--------------------------+  +--------------------------+  +--------------------------+         |
|  | District 1 (Ahmedabad)   |  | District 2 (Vadodara)    |  | District 33 (Valsad)     |         |
|  | - 2,500 Multi-vendor Cams|  | - 1,800 Multi-vendor Cams|  | - 1,200 Border Cameras   |         |
|  | - Edge AI / ANPR Engine  |  | - Edge AI / ANPR Engine  |  | - Edge AI / ANPR Engine  |         |
|  | - 15-30 Day NVR Buffer   |  | - 15-30 Day NVR Buffer   |  | - 15-30 Day NVR Buffer   |         |
|  +------------+-------------+  +------------+-------------+  +------------+-------------+         |
|               |                             |                             |                       |
|               +-----------------------------+-----------------------------+                       |
|                                             | (Metadata / Plate Sightings: ~8 Kbps per cam)       |
|                                             v                                                     |
|  [TIER 2: 4 REGIONAL INTELLIGENCE HUBS]                                                           |
|  - North Gujarat Hub (Gandhinagar)       - South Gujarat Hub (Surat)                              |
|  - Central Gujarat Hub (Vadodara)        - Saurashtra & Kutch Hub (Rajkot)                        |
|  - In-Memory Event Streaming (Kafka / Redis Streams)                                              |
|  - VAHAN & eGujCop Hotlist Caching (Sub-millisecond Plate Lookups)                                |
|                                             |                                                     |
|                                             v                                                     |
|  [TIER 3: CENTRAL COMMAND & CONTROL CENTER (GANDHINAGAR - NETRAM)]                                |
|  - PostgreSQL + PostGIS Core Registry & Spatial Sighting Store                                    |
|  - Cross-Camera Movement Correlation & Journey Reconstructor Engine                               |
|  - Real-Time Law Enforcement Alert Dispatch & Patrol Routing                                      |
|  - Section 65B Digital Evidence Vault with SHA-256 Cryptographic Chain of Custody                 |
|  - Unified C4I Video Wall (Low-Latency On-Demand Video Pull via WebRTC/HLS)                       |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Ingestion & Interoperability Architecture (Model 3)

### 2.1 Connector Adapter Layer
To ensure complete vendor-neutrality and prevent vendor lock-in, the GIVIN Connector Layer abstracts camera hardware into 4 standard interface adapters:
1. **RTSP / RTP Adapter**: Standard H.264 / H.265 video transport over TCP/UDP for modern IP cameras.
2. **ONVIF Profile S/G/T Adapter**: Device discovery, PTZ positioning, and analytics metadata extraction.
3. **VMS SDK Adapter**: REST and WebSocket plugins for commercial VMS platforms (Milestone XProtect, Genetec Security Center, Qognify, Nx Witness).
4. **Legacy Analog / DVR Encoders**: Captures multi-channel video from legacy analog installations via H.264 edge encoders without camera replacement.

### 2.2 Dual-Stream Profile Strategy
- **Sub-Stream (Standard Monitoring)**: 720p @ 10-15 fps utilized for routine video wall overview and AI detection pipeline.
- **Main Stream (Forensic Recording)**: 1080p/4K @ 25 fps retained in local edge storage and pulled across the WAN only when an active hotlist match is triggered.

---

## 3. AI Video Analytics & ANPR Pipeline

### 3.1 Detection & Classification Stage
- Vehicles are localized using high-speed CNN models (YOLO / TensorRT architecture) optimized for edge deployment.
- Objects are classified into: *Sedan, SUV, Motorcycle, Commercial Truck, Bus, Auto-Rickshaw*.

### 3.2 Plate Crop & Optical Normalization Stage
- ANPR plate detector locates the High Security Registration Plate (HSRP) region.
- Bilateral filtering and adaptive thresholding correct for variable illumination (nighttime headlights, sun glare, rain).
- Positional regex validation (`^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$` and `22BH...`) validates state codes and alphanumeric sequencing.
- Optical disambiguation resolves character confusion (e.g. distinguishing `8` vs `B` and `0` vs `O`).

---

## 4. Watchlist Correlation & Alert Lifecycle

### 4.1 Integration with Law Enforcement Databases
GIVIN interfaces with external state and national databases via secure, read-only RESTful message queues:
- **VAHAN**: National vehicle registry for stolen vehicle identification and registration verification.
- **SARTHI**: Driving license database.
- **eGujCop / CCTNS**: Gujarat Police crime records, FIRs, and wanted criminal registries.
- **AFIS / NAFIS**: Biometric criminal tracking hotlists.

### 4.2 Alert Lifecycle State Machine
```
   [SIGHTING DETECTED]
           |
           v
  [WATCHLIST CHECK] ---> (No Match) ---> [STORE AS SIGHTING]
           |
     (Match Found)
           |
           v
      [STATUS: NEW]  (Audible & Visual Alarm in Command Center)
           |
           v
  [STATUS: ACKNOWLEDGED]  (Officer Takes Ownership within 30s)
           |
           v
  [STATUS: INVESTIGATING] (Patrol / Interceptor PCR Van Dispatched)
           |
     +-----+-----+
     |           |
     v           v
[RESOLVED]  [FALSE POSITIVE]
```

---

## 5. Cross-Camera Correlation & Vehicle Journey Reconstruction

### 5.1 Temporal-Spatial Tracking Algorithm
When a designated registration number is queried:
1. GIVIN queries all chronologically ordered sightings across the integrated 50 cameras.
2. Computes the Haversine great-circle distance between consecutive camera coordinates.
3. Calculates transit time and velocity between checkpoints.
4. Detects anomalies (e.g., transit speeds exceeding 160 km/h flag potential cloned plates or stolen registration tags).
5. Compiles a GeoJSON route and animates the trajectory on the interactive GIS map.

---

## 6. Cybersecurity & Section 65B Evidence Compliance

### 6.1 Legal Admissibility (Section 65B Indian Evidence Act / Section 63 BSA 2023)
Electronic CCTV evidence submitted in Indian courts requires strict statutory compliance:
- **NTP Time Synchronization**: Recording servers synchronize clocks with standard national time servers.
- **SHA-256 Hashing**: Every cropped frame and detection record is stamped with a SHA-256 hash upon capture.
- **HMAC Digital Signatures**: A tamper-evident signature incorporates camera ID, timestamp, plate text, image hash, and officer identity.
- **One-Click Certificate Generation**: The platform generates a court-ready Section 65B Certificate complete with statutory declarations.

### 6.2 Zero-Trust Security Architecture
- Department- and Role-Based Access Control (RBAC): Super Admin, District SP, Police Inspector, Operator, Auditor.
- TLS 1.3 encryption in transit for all APIs and video relays.
- AES-256 encryption for evidence snapshots at rest.
- Immutable, append-only audit trail logging every search, export, and status update.

---

## 7. Statewide Sizing for ~80,000 Cameras

| Metric | Brute-Force Central Streaming (Model 4) | GIVIN Hybrid Architecture | Optimization |
| :--- | :--- | :--- | :--- |
| **Network Bandwidth** | 320.0 Gbps | **5.44 Gbps** | **98.3% Reduction** |
| **Central Datacenter Storage** | 103.6 PB (30 Days) | **4.1 PB (Incidents only)** | **96.0% Reduction** |
| **Central GPU Servers** | 5,000 GPU Nodes | **132 District Nodes** | **97.4% Reduction** |
| **Estimated Annual Infrastructure Cost** | ~₹215 Crores | **~₹27.8 Crores** | **₹187+ Crores Saved Annually** |

---

## 8. Department Onboarding Requirements (Appendix C)
Participating Gujarat departments supply:
1. Camera inventory with static IP/DNS endpoints and RTSP URLs.
2. Precise GPS coordinates (latitude/longitude) and installation height/azimuth.
3. Hardware vendor, model, resolution, and current VMS platform.
4. Storage tier specifications and mandated retention policy (7, 15, or 30 days).
5. Secure credential tokens via encrypted vault handoff.
