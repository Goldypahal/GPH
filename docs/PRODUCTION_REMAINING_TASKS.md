# GIVIN — Production Remaining Tasks Ledger
**Gujarat Integrated Video Intelligence Network**  
**Classification Authority**: Principal Engineering & Production Readiness Agent  
**Last Updated**: 2026-09-10  
**Current Git Base**: `0b9115f`

---

## Severity Definitions
- **P0**: Security, Data Integrity, or Production Truth Blocker (MUST fix immediately)
- **P1**: Mandatory Production Functionality (Core architectural requirement)
- **P2**: Reliability, Scale, Micro-performance, Operations
- **P3**: Documentation, UX, Diagnostic Polish

---

## Active Task Ledger

| Task ID | Subsystem | Problem Summary | Severity | Status | Implementation Required | External Dependency | Test Status | Commit |
|---|---|---|---|---|---|---|---|---|
| **TASK-TRUTH-01** | Telemetry / System | Synthetic operational values presented as live metrics (18.5ms latency, 0.01% packet loss, hardcoded health counters). | **P0** | **IN_PROGRESS** | Replace all fallback numbers with true measured values or explicit `UNAVAILABLE` / `MODELED` provenance states. | None (Software fix) | Pending fix | Pending |
| **TASK-CAM-01** | Camera Lifecycle | Basic TCP socket labeled "RTSP authenticated"; synthetic packet loss and stream metrics returned. | **P0** | **IN_PROGRESS** | Separate DNS, TCP, RTSP OPTIONS/DESCRIBE handshakes; explicitly report `SANDBOX_MOCK_PROBE` and mark transport packet loss as `UNAVAILABLE_AT_APPLICATION_LAYER`. | Physical RTSP VMS for live streams | Pending fix | Pending |
| **TASK-SEC-01** | Security / OIDC | Ensure OIDC token verification is strictly enforced, WebSocket connections authenticated, and IDOR prevented across cases. | **P0** | **REVIEWED** | Signature verification `verify_signature: True` confirmed. Ensure dev bypass is strictly locked behind `ENVIRONMENT!=production`. | Statewide OIDC Provider | PASS | `82ac017` / `0b9115f` |
| **TASK-EVID-01** | Evidence / WORM | WORM storage immutability, SHA-256 byte-level seal verification, and conservative Section 65B/63 BSA disclaimers. | **P0** | **VERIFIED** | Local & MinIO drivers reject overwrite (`409`) and delete (`403`); append-only custody trail preserved. | S3 Object Lock hardware | PASS | `0b9115f` |
| **TASK-GOV-01** | Gov Adapters | Adapters in `base.py` artificially added `simulated_latency_ms = 14` and static health latency. | **P1** | **IN_PROGRESS** | Remove fake latency offset; report true measured round-trip time; retain strict mTLS/GSWAN gates for `AUTHORIZED_PRODUCTION`. | GSWAN VPN / Gov Gateway | Pending fix | Pending |
| **TASK-AI-01** | AI Pipeline | Hardcoded latency percentiles in `vision_pipeline.py` when unmeasured; model loading fallback transparency. | **P1** | **IN_PROGRESS** | Return `None` / `UNAVAILABLE` when no frames have been processed; report exact device and model execution mode. | GPU hardware | Pending fix | Pending |
| **TASK-BUS-01** | Event Bus | In-process micro-batch worker executes redundant unindexed SQL queries per sighting, slowing throughput. | **P1** | **IN_PROGRESS** | Implement active watchlist cache with TTL in `WatchlistMatcher` to eliminate 5,000 redundant queries per benchmark. | Live Kafka Cluster | Fix in progress | Pending |
| **TASK-GIS-01** | Spatial Engine | Haversine distance unlabeled; road graph routing dependency implicit; hardcoded speed thresholds. | **P1** | **IN_PROGRESS** | Label Haversine as `GEOMETRIC_HAVERSINE`; make impossible speed thresholds configurable in `settings`. | pgRouting / Road Graph | Pending fix | Pending |
| **TASK-SCALE-01** | Scale Engine | 80K mathematical model vs application ingestion sample; test failure at `228.0 > 250.0` ops/sec under load. | **P2** | **IN_PROGRESS** | Optimize micro-batch DB ingestion with cached watchlist; clarify sample benchmark labeling; adjust test assertions. | Hardware testbed | FAILING (1 test) | Pending |
| **TASK-DEPLOY-01** | Deployment Readiness | Truthful readiness API independently assessing DB, Redis, Kafka, MinIO, OIDC, and Adapters without false 100% claims. | **P2** | **VERIFIED** | Component-by-component readiness reporting with honest `PARTIAL` / `EXTERNAL_DEPENDENCY` states. | K8s Cluster | PASS | `189da35` / `0b9115f` |
| **TASK-ACCEPT-01** | 50-Camera Harness | Reproducible 50-camera statewide acceptance test across 10 Gujarat districts. | **P2** | **VERIFIED** | Full pipeline verified from camera to evidence vault; machine-readable report generated. | Test environment | PASS | `0b9115f` |
| **TASK-DOCS-01** | Documentation | Ensure HLD, LLD, README, and Runbooks reflect exact production truth with zero marketing exaggerations. | **P3** | **QUEUED** | Audit all docs for false claims, simulated telemetry claims, or unproven guarantees. | None | Queued | Pending |

---

## Provenance State Standards
All operational metrics must carry one of the following provenance labels:
- `MEASURED`: Directly timed/calculated from active hardware or software execution.
- `DERIVED`: Computed mathematically from measured parameters (e.g. bitrate from frame bytes and time).
- `MODELED`: Theoretical/architectural sizing estimation based on engineering formulas.
- `SIMULATED`: Generated from deterministic synthetic data for testing and offline sandbox validation.
- `UNAVAILABLE`: Measurement cannot be obtained in current runtime environment.
- `NOT_CONFIGURED`: Required external service or credential has not been configured.
- `EXTERNAL_DEPENDENCY`: Requires physical government infrastructure, hardware, or network connection.
