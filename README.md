# GIVIN — Gujarat Integrated Video Intelligence Network
### Statewide CCTV Integration, AI Video Analytics & Real-Time Intelligence Platform
**Gujarat Police Innovation Hackathon 2026**

---

## Executive Summary
**GIVIN** is a statewide, vendor-neutral video intelligence platform engineered to solve Problem Statement #1 of the **Gujarat Police Innovation Hackathon 2026**.

The Government of Gujarat currently operates CCTV cameras across **26 independent Government Departments** (Home Department, Food & Civil Supplies, RTO, Municipalities, Maritime Board, Mines, Forest, etc.). These ecosystems feature heterogeneous camera types, disparate VMS platforms (Milestone, Genetec, Qognify, Nx Witness, local NVRs), multi-vendor hardware (Hikvision, Dahua, CP Plus, Axis, Honeywell, Hanwha), diverse protocols (RTSP, ONVIF, HTTP-FLV), and varying retention periods.

Instead of an unaffordable "Model 4" brute-force central stream ingestion (which for 80,000 cameras would require **320 Gbps** of WAN bandwidth costing hundreds of crores annually), GIVIN deploys an engineered **Hybrid Edge-Metadata Architecture**:
1. **Model 1 (CCTV Asset Registry & GIS)**: Maps every camera's exact latitude, longitude, department ownership, field of view, and health across Gujarat.
2. **Model 3 (Protocol-Agnostic Connectors)**: Interfaces with multi-vendor NVRs/VMS without replacing departmental equipment or causing vendor lock-in.
3. **Edge/Regional Distributed AI**: Vehicle detection and ANPR run at edge gateways/NVRs, transmitting lightweight JSON metadata events upstream (saving **98.3% of network bandwidth**).
4. **Model 2 (Command & Control Center)**: Unified C4I dashboard, dynamic GIS trajectory mapping, sub-second watchlist correlation against **VAHAN, SARTHI, eGujCop (CCTNS), and AFIS/NAFIS**, and court-admissible Section 65B evidence packaging.

---

## Technical Credibility & Scope Statement

> [!IMPORTANT]
> **Engineering Distinction: Modeled Capacity vs Measured Performance**
> - **Statewide Capacity Model**: The 80,000-camera bandwidth (5.44 Gbps), storage (2.07 PB), and TCO comparisons are **mathematical sizing models** based on derived traffic characteristics (2 sightings/sec/camera metadata, 1.2 KB JSON payloads, 2% alert hit rate with 35 KB image crops, and +0.5 Gbps burst headroom). Cost estimations are illustrative engineering models subject to vendor quotes and government procurement processes.
> - **In-Process Synthetic Ingestion Benchmark**: The platform includes a live application-layer synthetic stress-test engine (`POST /api/system/scale-benchmark/run`) measuring in-process dispatch, queue ingestion, and per-event latency.
> - **Physical Infrastructure Deployment Testing**: Validating physical 80,000 physical RTSP streams, multi-broker Kafka disk I/O, and inter-city WAN latency requires staged deployment onto physical clustered hardware (e.g. at the Gujarat State Data Centre).

---

## Software Implementation vs Production Deployment Readiness

| Capability Domain | Software Implementation Status (Verified in Code) | Production Staged Deployment Roadmap |
| :--- | :--- | :--- |
| **Spatial & Relational Database** | ✅ Complete: SQLite + PostGIS schema abstraction, Alembic migrations | 🔲 Deploy PostgreSQL 16 + PostGIS cluster with patroni HA on GSDC |
| **Edge AI & Computer Vision** | ✅ Complete: Dedicated YOLO plate detector, CLAHE deskewer, ByteTrack, temporal OCR voting | 🔲 Flash optimized TensorRT models to District Jetson Orin / Hailo NPU edge gateways |
| **Cross-Camera Intelligence** | ✅ Complete: Camera network graph ($P(C_j \mid C_i)$), cloned plate physical impossibility anomaly detection, dynamic pursuit containment | 🔲 Ingest live road topology graph from Gujarat State Road Development Corporation (GSRDC) |
| **Enterprise RBAC & Security** | ✅ Complete: 5-tier role hierarchy, fine-grained permission matrix, 26-dept federation lifecycle, SHA-256 audit hash chain | 🔲 Integrate with Gujarat State Single Sign-On (SSO) / Keycloak OIDC and HashiCorp Vault |
| **Event Streaming Backbone** | ✅ Complete: Resilient dual-mode broker, partitioned topics, micro-batch worker, Dead Letter Queue (DLQ) & replay APIs | 🔲 Provision multi-broker Apache Kafka / Redpanda KRaft cluster with 3x replication |
| **Government Database Integration** | ✅ Complete: Stateful VAHAN, SARTHI, eGujCop, AFIS adapters with Redis caching, HMAC-SHA256 signatures, Unified Intel Dossier | 🔲 Exchange mutual TLS certificates and secure VPN gateway credentials with NIC / CCTNS Gujarat |
| **Court Evidence & Section 65B** | ✅ Complete: Automated case creation from alert, timeline evidence linkage, Section 65B ZIP bundle export | 🔲 Formally register C4I digital certificate authorities with Gujarat Forensic Sciences University / FSL |
| **Statewide Sizing & Stress Testing** | ✅ Complete: 80k mathematical model, in-process synthetic stress test (>2,500 MPS, measured per-event p95 latency) | 🔲 Execute multi-node distributed load generation across 33 district edge clusters |

---

## 7-Phase Roadmap Delivery Overview

- **Phase A — Foundation Substrate**: PostGIS spatial models, Redis temporal state, MinIO object store abstraction, multi-vendor camera connector factory.
- **Phase B — Real AI Vision Pipeline**: Dedicated license plate detector, CLAHE deskewing preprocessor, ByteTrack multi-camera persistent tracking, temporal OCR voting consensus.
- **Phase C — Cross-Camera Intelligence**: Statewide camera adjacency graph, cloned plate teleportation detection, 5/10/15-minute tactical pursuit containment perimeters.
- **Phase D — Enterprise RBAC & Security**: 5-tier role hierarchy (Officer to Chief), fine-grained permission guards, 26-department camera federation, blockchain-style audit hash chain.
- **Phase E — Resilient Event Streaming**: Partitioned topics (`givin.sightings.raw`, `givin.sightings.normalized`, `givin.alerts.triggered`, `givin.telemetry.camera`, `givin.dlq`), micro-batch bulk worker, DLQ quarantine & replay engine.
- **Phase F — Government Integrations & Workflows**: Stateful VAHAN, SARTHI, eGujCop, AFIS adapters with Redis TTL caching and HMAC-SHA256 source signatures; Unified Threat Dossier; Section 65B court evidence ZIP export.
- **Phase G — Scale Proof & Command Center UI**: 80,000-camera capacity model, in-process synthetic benchmark engine, interactive stress test in Command Center UI, and tender compliance specification matrix.

---

## Verification & Automated Test Suite (31/31 Passing)

Run the full platform test suite covering all 7 phases:

```powershell
pytest tests/test_substrate_phase_a.py tests/test_vision_phase_b.py tests/test_cross_camera_phase_c.py tests/test_rbac_phase_d.py tests/test_event_streaming_phase_e.py tests/test_gov_and_cases_phase_f.py tests/test_scale_and_system_phase_g.py -v
```

All 31 test suites pass with 100% success in ~6 seconds:
- **Phase A**: Database substrate health, local storage, Redis state, camera connectors, deployment readiness.
- **Phase B**: Dedicated plate detector, plate preprocessor, ByteTrack, temporal OCR fusion, end-to-end vision pipeline, AI metrics API.
- **Phase C**: Camera network graph, cloned plate detection, pursuit containment perimeters, cross-camera endpoints.
- **Phase D**: JWT auth & roles, fine-grained permission denial, department camera federation lifecycle, blockchain audit chain tamper detection.
- **Phase E**: Stream broker topics & partitions, micro-batch ingestion throughput, DLQ quarantine & replay, streaming metrics API.
- **Phase F**: Gov adapters caching & HMAC signatures, unified intel bundle risk scoring, case-from-alert creation, Section 65B ZIP export.
- **Phase G**: Scale mathematical sizing model, synthetic ingestion throughput, benchmark API endpoints with target annotations, end-to-end scale calculator.

---

## Quick Start & Local Execution

### Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox)

### Launching the Command Center
```powershell
python backend/run_server.py
```

- **Command Center Dashboard**: `http://127.0.0.1:8000/`
- **Interactive OpenAPI / Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **Tender Compliance Specs**: `GET http://127.0.0.1:8000/api/system/scale-benchmark/specs`
- **Unified Gov Intel Dossier**: `GET http://127.0.0.1:8000/api/system/gov/intel-bundle/GJ01AB1234`
