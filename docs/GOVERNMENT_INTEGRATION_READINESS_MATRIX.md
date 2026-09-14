# GIVIN — Government Integration Readiness Matrix

**Classification System**:
- `NOT_STARTED`: No adapter or interface defined.
- `INTERFACE_DEFINED`: Abstract interface or endpoint signatures exist.
- `CONTRACT_TESTED`: Schema validation, rate limiting, and fail-closed tests pass.
- `SANDBOX_READY`: Successfully connected to staging/sandbox mock service with synthetic records.
- `CREDENTIALS_REQUIRED`: Production code ready, blocked on official agency client certificates/API keys.
- `NETWORK_REQUIRED`: Production code ready, blocked on dedicated State WAN (GSWAN) VPN tunnel.
- `AUTHORIZATION_REQUIRED`: Cryptographic & network prerequisites ready, blocked on departmental MoRTH/MHA MoU clearance.
- `LIVE_INTEGRATION_VALIDATED`: Real production queries verified with authorized live credentials. *(Never claimed without active clearance).*

---

## 1. Readiness Classification Summary

| # | External Database / Agency | Provider / Authority | Current Classification | Security Boundary | Fail-Closed Verified |
|---|---|---|---|---|---|
| 1 | **VAHAN 4.0** (National Vehicle Registry) | MoRTH / NIC | **CONTRACT_TESTED & SANDBOX_READY** (Prod: `CREDENTIALS_REQUIRED`) | mTLS + GSWAN | **YES** (Raises `RuntimeError`) |
| 2 | **SARATHI 4.0** (Driving License Database) | MoRTH / NIC | **CONTRACT_TESTED & SANDBOX_READY** (Prod: `CREDENTIALS_REQUIRED`) | mTLS + GSWAN | **YES** (Raises `RuntimeError`) |
| 3 | **CCTNS** (Crime & Criminal Tracking Network) | NCRB / Ministry of Home Affairs | **CONTRACT_TESTED & SANDBOX_READY** (Prod: `NETWORK_REQUIRED`) | IPsec VPN + OAuth2 | **YES** (Raises `RuntimeError`) |
| 4 | **eGujCop** (State CCTNS / Crime Hotlists) | Gujarat Police / State Crime Records Bureau (SCRB) | **CONTRACT_TESTED & SANDBOX_READY** (Prod: `AUTHORIZATION_REQUIRED`) | GSWAN + Token Auth | **YES** (Raises `RuntimeError`) |
| 5 | **AFIS** (State Automated Fingerprint System) | Gujarat State CID Crime / SCRB | **CONTRACT_TESTED & SANDBOX_READY** (Prod: `CREDENTIALS_REQUIRED`) | GSWAN + NIST WSQ | **YES** (Raises `RuntimeError`) |
| 6 | **NAFIS** (National Automated Fingerprint System) | NCRB / Central Finger Print Bureau (CFPB) | **CONTRACT_TESTED & SANDBOX_READY** (Prod: `CREDENTIALS_REQUIRED`) | mTLS + GSWAN | **YES** (Raises `RuntimeError`) |
| 7 | **GSWAN / 1-Net Boundary** | Gujarat Informatics Limited (GIL) | **INTERFACE_DEFINED** (Prod: `NETWORK_REQUIRED`) | Site-to-site IPsec tunnel | **YES** (Strict gateway check) |

> [!CAUTION]
> **Zero Live Integration Claim**: No adapter is classified as `LIVE_INTEGRATION_VALIDATED`. In compliance with Non-Negotiable Principle #8, GIVIN makes no false claims of live production access to national security databases during this hackathon evaluation.

---

## 2. Detailed Technical Adapter Specifications

### 2.1 VAHAN 4.0 (MoRTH / NIC)
- **Code Location**: `backend/app/services/gov_adapters/vahan_adapter.py`, `base.py`.
- **Target Endpoint**: `https://vahan.parivahan.gov.in/api/v4/vehicle`.
- **Schema Validation**: Registration number regex normalization (`^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$`).
- **PII Minimization**: Owner name masked (e.g. `Rameshwar S****`) in accordance with DPDP Act 2023. Chassis/engine numbers masked to last 4 digits.
- **Security**: mTLS Client Certificate (`GOV_MTLS_CERT_PATH`), Client Key (`GOV_MTLS_KEY_PATH`), and GSWAN VPN (`GSWAN_VPN_ACTIVE=true`).
- **Fail-Closed Behavior**: When `mode=AUTHORIZED_PRODUCTION` and certificates/VPN are missing, queries immediately raise `RuntimeError` and log security audit event.
- **Caching & Rate Limiting**: Redis cache with 1-hour TTL (`CACHE_TTL_SEC=3600`), strict rate limiting at 120 req/min.

### 2.2 SARATHI 4.0 (MoRTH / NIC)
- **Code Location**: `backend/app/services/gov_adapters/sarathi_adapter.py`, `base.py`.
- **Target Endpoint**: `https://sarathi.parivahan.gov.in/api/v1/license`.
- **Returned Metadata**: License validity dates, authorized vehicle classes (`LMV`, `MCWG`), pending traffic challans count.
- **Privacy Controls**: Driver home address and biometric data strictly excluded from payload.
- **Fail-Closed Behavior**: Refuses execution in `AUTHORIZED_PRODUCTION` mode without verified government transport infrastructure.

### 2.3 CCTNS (NCRB / MHA)
- **Code Location**: `backend/app/services/gov_adapters/cctns_adapter.py`, `base.py`.
- **Target Endpoint**: `https://cctns.gov.in/api/v2/national-vehicle-fir-check`.
- **Criminal Hotlist Cross-Reference**: Matches plate against national stolen vehicle and crime database.
- **Statutory Audit**: Records requesting police officer badge number, FIR reference number, and cryptographic signature for every query.

### 2.4 eGujCop (Gujarat Police / SCRB)
- **Code Location**: `backend/app/services/gov_adapters/egujcop_adapter.py`, `base.py`.
- **Target Endpoint**: `https://police.gujarat.gov.in/cctns/api/v2/crimes`.
- **Integration**: Local state police FIR database, jurisdiction police station lookup, BNS/IPC penal charges mapping.
- **Readiness**: Software adapter verified against Gujarat Police test dataset (`FIR-2026/AHM-CRIME/0981`).

### 2.5 AFIS & NAFIS (State & National Fingerprint Registries)
- **Code Location**: `backend/app/services/gov_adapters/afis_adapter.py`, `nafis_adapter.py`.
- **Purpose**: Biometric suspect identification support for serious criminal investigations linked to suspect vehicles.
- **Access Control**: Restricted to `INVESTIGATOR` role and above; requires active case reference number.

---

## 3. Production Deployment Roadmap for Government Gateways

To transition adapters from `CONTRACT_TESTED & SANDBOX_READY` to `LIVE_INTEGRATION_VALIDATED`, the following administrative and network procedures must be completed:

1. **Phase 1: GSWAN Network Provisioning**: Establish dedicated site-to-site IPsec tunnel between GIVIN central datacenter (Gandhinagar) and GSDC (Gujarat State Data Centre).
2. **Phase 2: NIC Digital Certificate Issuance**: Obtain official government-issued X.509 client certificates from National Informatics Centre (NIC).
3. **Phase 3: Formal Departmental Clearance**: Execute inter-departmental data-sharing agreements between Home Department, Transport Department (MoRTH), and SCRB.
4. **Phase 4: Pilot Staging Validation**: Execute end-to-end sandbox verification against Gujarat Police UAT environment prior to cutover.
