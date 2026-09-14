# GIVIN 80,000 Virtual Camera Scale Test Plan

**Document Version**: 1.0.0  
**Classification**: Engineering Protocol / Scale Methodology  
**Target Architecture**: 80,000 Heterogeneous Surveillance Cameras Across 33 Gujarat Districts  

---

## 1. Objective & Scope

This document specifies the technical test plan for validating the **GIVIN software platform's capacity to accept, coordinate, ingest, and process 80,000 camera streams** without claiming physical road deployment of 80,000 physical IP cameras.

The test plan decouples **software architecture scalability** from **physical video decoding saturation**, verifying:
1. Connection & Session Scalability (80,000 persistent sessions, heartbeat pacing).
2. Event & Alert Throughput (1,000 to 100,000 sightings/second).
3. Frame-Reference Multiplexing (replaying benchmark frames across thousands of virtual cameras).
4. Edge vs. Central Storage Sizing (864 TB/day central vs. 14.7 TB/day hybrid edge).
5. Chaos, Link Severance & Self-Healing Convergence.

---

## 2. 33-District Partitioning Model

Rather than modeling a flat, unrealistic 80,000 camera pool, GIVIN partitions cameras across all **33 Gujarat administrative districts** with uneven, realistic density allocations:

| Region / District | Cameras | RTO Code | Gateway Subnet | Operational Profile |
| :--- | :--- | :--- | :--- | :--- |
| **Ahmedabad** | **8,000** | GJ01 | `10.240.1.0/24` | Mega-Metropolitan Commercial & Transit Hub |
| **Surat** | **7,000** | GJ05 | `10.240.2.0/24` | Industrial, Diamond & Port Logistics Corridor |
| **Vadodara** | **5,000** | GJ06 | `10.240.3.0/24` | Central Gujarat Petrochemical & Transit Spine |
| **Rajkot** | **4,000** | GJ03 | `10.240.4.0/24` | Saurashtra Manufacturing & Highway Crossroads |
| **Gandhinagar** | **3,300** | GJ18 | `10.240.5.0/24` | State Capital & High-Security Government Zone |
| **Kutch** | **3,200** | GJ12 | `10.240.6.0/24` | International Border & Major Maritime Ports |
| **Bhavnagar** | **3,000** | GJ04 | `10.240.7.0/24` | Coastal & Port Surveillance Zone |
| **Jamnagar** | **2,600** | GJ10 | `10.240.8.0/24` | Petroleum Refining & Defense Airbase Corridor |
| **Junagadh** | **2,500** | GJ11 | `10.240.9.0/24` | Tourism & Pilgrimage Transit Route |
| **Bharuch** | **2,500** | GJ16 | `10.240.10.0/24` | Heavy Chemical Belt & Golden Corridor (NH-48) |
| **Anand / Banaskantha** | **4,600** | GJ23/GJ08 | `10.240.11-12/24` | Dairy Hub & Northern Interstate Border |
| **Remaining 21 Districts** | **34,300** | GJ02..GJ37 | `10.240.13-33/24` | Regional Police Headquarter Jurisdictions |
| **Total Statewide** | **80,000** | **Statewide** | **GSWAN Ring** | **100% Comprehensive Coverage** |

---

## 3. Test Modes Description

### Mode 1: Connection & Session Scalability
- **Fleet Size**: 80,000 virtual camera clients.
- **Protocol**: TCP / RTSP keep-alive sessions with 0.1–1.0 Hz heartbeat pacing.
- **Evaluation Criteria**: Memory allocation per session (< 1 KB/session), connection establishment rate (> 10,000 sessions/sec), and zero socket leakage.

### Mode 2: Metadata & Sighting Ingestion Throughput
- **Load Model**: Simulates 1 sighting every 5 seconds per camera (16,000 sightings/sec aggregate).
- **Burst Tiers**:
  - **Normal**: 1,000 events/sec
  - **Busy**: 10,000 events/sec
  - **Major Incident / VIP**: 50,000 events/sec
  - **Worst-Case Burst**: 100,000 events/sec
- **Evaluation Criteria**: Queue depth, consumer lag, watchlist matching latency (p95 < 15 ms), and alert creation.

### Mode 3: Frame-Reference Multiplexing Replay
- **Input**: Real frames from CityFlow / BMD-45 benchmark datasets.
- **Mechanism**: Frames are multiplexed across 80,000 virtual cameras with unique container PTS timestamps.
- **Evaluation Criteria**: Tests the complete event generation, spatial normalization, and journey correlation pipeline without saturating video decoders.

### Mode 4: Mixed Real Inference & Virtual Metadata
- **Workload**: 50 physical/reference streams processed by real YOLO11 + PaddleOCR inference workers, combined with 80,000 virtual metadata clients.
- **Evaluation Criteria**: Independent measurement of GPU utilization/VRAM and proof that edge processing isolates central servers from video overload.

### Mode 5: Failure, Network Chaos & Recovery
- **Fault Injections**:
  - 5% simultaneous camera disconnect (4,000 cameras).
  - 10% concurrent reconnection storm (8,000 cameras thundering herd).
  - Network jitter / 20% packet loss on 5% cameras.
  - Out-of-order PTS timestamps and duplicate events.
  - Complete district edge-node isolation (Dang district 700 cameras severed).
- **Evaluation Criteria**: Self-healing convergence, dead-letter queue containment, and zero pipeline crash.

---

## 4. Execution & Reporting Protocol

The test suite is executed using the master script:
```bash
python scripts/run_80k_virtual_camera_test.py --output artifacts/scale-80k/
python scripts/summarize_scale_results.py
```
Output artifacts are persisted to `artifacts/scale-80k/scale_80k_results.json` and `artifacts/scale-80k/summary.md`.
