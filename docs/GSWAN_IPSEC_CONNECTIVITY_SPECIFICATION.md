# GSWAN (Gujarat State Wide Area Network) IPsec Connectivity Specification

**Document Version**: 1.0.0  
**Classification**: Official / Law Enforcement Restricted  
**Release Reference**: `givin-hackathon-2026-rc2`  
**Governing Authority**: Gujarat Informatics Limited (GIL) & Gujarat State Police Department  

---

## 1. Executive Summary

GIVIN (Gujarat Integrated Video Intelligence Network) operates across 33 administrative districts and requires secure, encrypted communication to the central **Gujarat State Data Centre (GSDC)** in Gandhinagar to access sovereign databases (VAHAN, SARATHI, CCTNS, eGujCop, AFIS, NAFIS).

This document specifies the **RFC 7296 IKEv2 site-to-site IPsec VPN** architecture connecting GIVIN District C4I Edge Nodes to the GSWAN backbone.

> [!IMPORTANT]
> **Truth-in-Engineering Disclosure**:
> GIVIN provides production-grade IPsec configuration templates (`deploy/ipsec/ipsec.conf`), Kubernetes gateway manifests (`k8s/09-gswan-ipsec-gateway.yaml`), automated diagnostics (`backend/app/services/gswan_connector.py`), and boundary tests.
> **Physical packet routing across GSWAN cannot occur on unpeered test environments.** Establishing a live connection requires physical termination on a GSWAN Point of Presence (PoP), an official MoU with Gujarat Informatics Limited (GIL), and departmental X.509 certificates.

---

## 2. Architecture & Topology

```
+-----------------------------------------------------------------------------------+
|                        GIVIN DISTRICT EDGE NODES & C4I                             |
|  Local Subnet: 10.240.0.0/16                                                      |
|  - Edge Inference Cluster (YOLO11n + ByteTrack)                                  |
|  - WORM Digital Evidence Vault (MinIO Section 63/65B BSA)                        |
|  - Local Control Room Operators                                                   |
+----------------------------------------+------------------------------------------+
                                         |
                                         v
               +----------------------------------------------------+
               | strongSwan IPsec VPN Gateway Pod / Appliance       |
               | (k8s/09-gswan-ipsec-gateway.yaml, NET_ADMIN)       |
               +-------------------------+--------------------------+
                                         |
                       IKEv2 / IPsec Encrypted ESP Tunnel
                       AES-256-GCM-16 + SHA-384 + MODP-2048
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                       GSWAN STATEWIDE OPTICAL FIBER BACKBONE                      |
|                     Managed by Gujarat Informatics Limited (GIL)                  |
+-------------------+-------------------------------------------+-------------------+
                    |                                           |
         Primary Link (Gandhinagar)                  Secondary Link (Failover DR)
                    |                                           |
                    v                                           v
+---------------------------------------+   +---------------------------------------+
| Gujarat State Data Centre (GSDC)      |   | GSWAN Disaster Recovery Hub           |
| Gandhinagar (10.100.1.1)              |   | Vadodara (10.100.2.1)                 |
| Subnets: 10.0.0.0/8, 172.16.0.0/12    |   | Subnets: 10.0.0.0/8, 172.16.0.0/12    |
| - National VAHAN Vehicle Registry     |   | - Backup Federation Endpoints         |
| - National SARATHI DL Registry        |   | - Cold Disaster Recovery State        |
| - CCTNS / eGujCop Gujarat Police DB   |   +---------------------------------------+
| - AFIS / NAFIS Biometric Repository   |
+---------------------------------------+
```

---

## 3. Cryptographic & Security Profiles

The strongSwan configuration strictly adheres to RFC 7296 and Ministry of Home Affairs (MHA) cybersecurity mandates:

| Parameter | Specification | Rationale |
| :--- | :--- | :--- |
| **Protocol** | **IKEv2** (Internet Key Exchange v2) | Eliminates legacy IKEv1 vulnerabilities; enables native NAT traversal and MOBIKE. |
| **Phase 1 Cipher** | `aes256gcm16-sha384-modp2048` | High-assurance 256-bit Galois/Counter Mode AEAD cipher with Diffie-Hellman Group 14. |
| **Phase 2 (ESP) Cipher** | `aes256gcm16-sha384` | Authenticated encryption with associated data; high throughput on hardware AES-NI. |
| **Dead Peer Detection (DPD)** | `delay=15s`, `timeout=60s`, `action=restart` | Automatically detects broken fiber links or power drops at district PoPs and re-keys. |
| **PFS (Perfect Forward Secrecy)** | Enabled | Compromise of long-term credentials does not compromise past session keys. |
| **IKE Lifetime** | 24 Hours (`rekey=yes`, `reauth=no`) | Standard GSDC rotation interval. |
| **ESP Lifetime** | 8 Hours | Limits cryptographic exposure under continuous streaming load. |
| **MSS Clamping** | **1360 Bytes** (`iptables -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360`) | Prevents MTU fragmentation over WAN MPLS/leased lines. |

---

## 4. Addressing & Subnet Routing Plan

| Segment | CIDR Block | Description |
| :--- | :--- | :--- |
| **GIVIN Local Edge LAN** | `10.240.0.0/16` | Internal Kubernetes Pod & Node network for GIVIN C4I edge processing. |
| **Primary GSDC Gateway** | `10.100.1.1` | Main ingress peering router at GSDC Gandhinagar. |
| **Secondary DR Gateway** | `10.100.2.1` | Disaster recovery ingress router at GSWAN Vadodara Hub. |
| **Remote Government Subnet 1** | `10.0.0.0/8` | Internal state government servers (eGujCop, CCTNS state nodal agency). |
| **Remote Government Subnet 2** | `172.16.0.0/12` | NIC dedicated transit network (VAHAN, SARATHI, NAFIS). |

---

## 5. Software Architecture & Enforcement

### 5.1 Diagnostic Connector (`backend/app/services/gswan_connector.py`)
GIVIN incorporates a continuous diagnostic service that monitors tunnel state:
- **Default State**: In unpeered environments, `is_tunnel_active()` reports `False` and returns `GSWAN_DISCONNECTED`.
- **Active State**: When `GSWAN_VPN_ACTIVE=true` and the network route to `10.100.1.1:500` is reachable, status reports `GSWAN_ACTIVE` with live millisecond latency.
- **Simulated Mode**: During offline acceptance and staging testing (`GSWAN_SIMULATED_TEST=true`), reports `GSWAN_SIMULATED_ACTIVE` with transparent data provenance labeling (`SIMULATED_TEST_HARNESS`).

### 5.2 Fail-Closed Boundary (`backend/app/services/gov_adapters/base.py`)
When any government database adapter (`VahanAdapter`, `eGujCopAdapter`, etc.) is placed into `AUTHORIZED_PRODUCTION` mode:
```python
if not (mtls_cert and os.path.exists(mtls_cert) and mtls_key and os.path.exists(mtls_key) and vpn_active):
    raise RuntimeError(
        f"[{self.service_name}] AUTHORIZED_PRODUCTION refuses to operate without verified government infrastructure. "
        f"Missing: {', '.join(missing)}. Operation rejected to prevent unauthorized data access."
    )
```
Queries are immediately rejected with an explicit error, preventing inadvertent plaintext data transmission over commercial WAN networks.

---

## 6. Official GIL Commissioning Checklist

To transition from the tested software candidate to live statewide packet flow:

1. [ ] **Departmental MoU**: Execute the bilateral Inter-Agency Data Exchange Agreement between Gujarat Police Department and Gujarat Informatics Limited (GIL).
2. [ ] **Physical Circuit Termination**: Terminate a dedicated 1 Gbps / 10 Gbps fiber circuit from the local district police headquarters to the nearest GSWAN PoP.
3. [ ] **Static Routing Registration**: Register `10.240.0.0/16` in the GSWAN BGP route reflector tables at GSDC Gandhinagar.
4. [ ] **PKI Certificate Issuance**: Generate CSR from GIVIN strongSwan gateway and obtain signed X.509 certificate from the Gujarat State Subordinate CA.
5. [ ] **Kubernetes Secret Mounting**: Provision `gswan-ipsec-secrets` containing `givin-node.crt` and `givin-node.key`.
6. [ ] **Deployment Rollout**: Apply `k8s/09-gswan-ipsec-gateway.yaml` and verify route table with `ipsec statusall`.
7. [ ] **Health Verification**: Query `GET /api/system/gswan-status` and confirm `status: "GSWAN_ACTIVE"`.
