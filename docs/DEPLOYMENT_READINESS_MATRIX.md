# GIVIN — Deployment & Operational Readiness Matrix

**Document Version**: 2.1.0  
**Scope**: Production Readiness Audit across Deployment Artifacts, Infrastructure Manifests & Dependency Resilience  
**Classification System**:
- `CONFIGURED`: Configuration files, Dockerfile, or Kubernetes YAML manifests exist.
- `LOCALLY_VALIDATED`: Tested on local developer machine / single-node container runtime.
- `INTEGRATION_VALIDATED`: Multi-container integration tested (e.g. docker-compose, CI cluster).
- `PHYSICALLY_ACCEPTANCE_TESTED`: Deployed and verified on physical production state infrastructure.

---

## 1. Deployment Tier Readiness Classifications

| Deployment Artifact / Tier | Code / Manifest Location | Current Classification | Verified Capabilities | Gaps / Pending Steps |
|---|---|---|---|---|
| **Base Container Image** | `Dockerfile` | **INTEGRATION_VALIDATED** | Multi-stage build, non-root user (`givin`), healthcheck instruction, python 3.11/3.13 | Staging registry push (`ghcr.io/goldypahal/givin`) |
| **Local Compose Stack** | `docker-compose.yml` | **INTEGRATION_VALIDATED** | API, PostgreSQL + PostGIS, Redis, MinIO WORM, healthy startup ordering | Tested on local Docker engine |
| **Kubernetes Base Manifests** | `k8s/base/` | **CONFIGURED & LINTED** | Deployments, Services, ConfigMaps, Secrets, Ingress with TLS termination | Cluster rollout onto live Kubernetes cluster |
| **Zero-Trust Network Policies** | `k8s/base/network-policy.yaml` | **CONFIGURED** | Default deny ingress, explicit port whitelisting, namespace isolation | CNI plugin (Calico/Cilium) enforcement check |
| **Pod Disruption Budgets** | `k8s/base/pdb.yaml` | **CONFIGURED** | `minAvailable: 1` across API and edge gateway pods | Multi-node disruption testing |
| **Health Probes** | `backend/app/main.py` (`/health`, `/healthz`, `/readyz`) | **INTEGRATION_VALIDATED** | Liveness, readiness, DB connectivity check, HTTP 503 on database drop | Integrated with K8s probe specs |
| **Backup & Disaster Recovery** | `deploy/backup-restore.sh` | **LOCALLY_VALIDATED** | Automated PostgreSQL WAL dump, MinIO object replication, sha256 checksums | Offsite immutable tape/SAN vault sync |

---

## 2. Infrastructure Dependency Resilience Matrix

| External Dependency | Startup Critical? | Core Flow Critical? | Fallback Behavior | Failure Mode | Recovery Behavior | Operator Status Visibility |
|---|---|---|---|---|---|---|
| **Primary Relational DB** (PostgreSQL / SQLite) | **YES** | **YES** | SQLite local WAL fallback in development; halts in production | Read-only / HTTP 503 | Automatic connection pool reconnect with exponential backoff | Emitted via `/health` (`database: READY/DEGRADED`) |
| **In-Memory Cache** (Redis) | **NO** | **NO** | In-memory thread-safe dictionary fallback (`InMemoryRedisState`) | Cache bypass; direct DB / source lookup | Reconnects on next operation | Logged in telemetry (`redis_connected: true/false`) |
| **Event Stream Broker** (Kafka / Redis) | **NO** | **NO** | In-memory asyncio queue with persistent SQLite DLQ buffer | Events queued in local dead-letter queue | Automatic replay via `POST /api/system/dlq/replay` | Metric emitted: `dlq_size`, `consumer_lag_ms` |
| **WORM Object Storage** (MinIO / S3) | **NO** | **YES** (Evidence) | Local encrypted filesystem vault (`LocalStorageBackend`) | Evidence capture delayed; frame hashes cached | Re-uploads cached packages when MinIO comes back online | Logged in `/api/evidence/health` |
| **Government Gateways** (VAHAN / CCTNS) | **NO** | **NO** | Fail-closed: returns `LOOKUP_FAILED` / `UNAVAILABLE`; never fabricates data | Network timeout (3s limit); circuit breaker opens | Retries with backoff (3 attempts); auto-closes circuit | Displayed as `SERVICE_UNAVAILABLE` on incident card |
| **AI GPU Acceleration** (NVIDIA TensorRT) | **NO** | **YES** (Real-time) | Transparent CPU PyTorch inference or deterministic simulation | Inference latency increases (45ms -> 220ms) | Auto-detects CUDA device on startup; switches device | Shown as `device: cuda:0` or `device: cpu` |

---

## 3. Production Hardening Checklist

- [x] **Non-Root Execution**: Container runs as unprivileged user `givin` (UID 10001).
- [x] **Production Secret Hygiene**: Startup probe rejects default or empty `SECRET_KEY` in `production` environment.
- [x] **Network Fencing**: Kubernetes `NetworkPolicy` restricts traffic between database, Redis, MinIO, and API.
- [x] **Immutability Enforcement**: MinIO / S3 WORM Object Lock prevents modification or deletion of statutory evidence packages.
- [x] **Graceful Shutdown**: SIGTERM handling flushes active tracking queues and closes database connections cleanly.
- [ ] **Physical GSWAN Acceptance**: Provisioning of dedicated IPsec leased lines connecting Gujarat State Data Centre (GSDC) to edge nodes. *(External government prerequisite).*
