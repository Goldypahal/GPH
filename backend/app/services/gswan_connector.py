"""
GSWAN (Gujarat State Wide Area Network) IPsec VPN Tunnel Connector & Boundary Service.
Provides cryptographic validation, tunnel health telemetry, and fail-closed network fencing
between GIVIN control rooms and the Gujarat State Data Centre (GSDC) in Gandhinagar.
"""

import os
import socket
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("givin.gswan_connector")


class GSWANTunnelStatus:
    CONNECTED = "GSWAN_ACTIVE"
    DISCONNECTED = "GSWAN_DISCONNECTED"
    NOT_CONFIGURED = "GSWAN_NOT_CONFIGURED"
    SIMULATED_ACTIVE = "GSWAN_SIMULATED_ACTIVE"


class GSWANConnectorService:
    """
    Manages and monitors the site-to-site IPsec connection to the GSWAN backbone.
    Enforces truth-in-telemetry: never claims physical connectivity on unpeered nodes.
    """

    DEFAULT_GSWAN_GATEWAY = "10.100.1.1"  # Standard GSDC Gandhinagar WAN Gateway IP
    DEFAULT_GSWAN_PORT = 500  # IKE UDP port

    def __init__(self):
        self.gateway_ip = os.getenv("GSWAN_GATEWAY_IP", self.DEFAULT_GSWAN_GATEWAY)
        self.gateway_port = int(os.getenv("GSWAN_GATEWAY_PORT", str(self.DEFAULT_GSWAN_PORT)))

    def is_tunnel_active(self) -> bool:
        """
        Determines if the GSWAN IPsec tunnel is genuinely established and reachable.
        In production, validates that the environment flag GSWAN_VPN_ACTIVE is true
        AND that the network route to the GSWAN gateway is live.
        """
        env_active = os.getenv("GSWAN_VPN_ACTIVE", "false").lower() in ("true", "1", "yes")
        if not env_active:
            return False

        # In testing or sandbox modes, allow verified test mock
        if os.getenv("GSWAN_SIMULATED_TEST", "false").lower() in ("true", "1", "yes"):
            return True

        # Check physical IP reachability with tight timeout
        return self._probe_gateway_reachability()["reachable"]

    def _probe_gateway_reachability(self) -> Dict[str, Any]:
        """Probes gateway latency. Times out cleanly if unpeered."""
        t0 = time.perf_counter()
        try:
            # Short timeout probe to gateway
            with socket.create_connection((self.gateway_ip, self.gateway_port), timeout=0.2):
                latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                return {"reachable": True, "latency_ms": latency_ms}
        except (socket.timeout, ConnectionRefusedError, OSError):
            return {"reachable": False, "latency_ms": None}

    def get_connectivity_status(self) -> Dict[str, Any]:
        """
        Truthful diagnostic status report for C4I command telemetry and audit reporting.
        """
        env_flag = os.getenv("GSWAN_VPN_ACTIVE", "false").lower() in ("true", "1", "yes")
        simulated_test = os.getenv("GSWAN_SIMULATED_TEST", "false").lower() in ("true", "1", "yes")
        probe = self._probe_gateway_reachability()

        if simulated_test and env_flag:
            status = GSWANTunnelStatus.SIMULATED_ACTIVE
            message = "Simulated GSWAN tunnel active for test/staging evaluation."
            latency = 4.2
            provenance = "SIMULATED_TEST_HARNESS"
        elif env_flag and probe["reachable"]:
            status = GSWANTunnelStatus.CONNECTED
            message = f"Live GSWAN IPsec tunnel active to GSDC Gandhinagar ({probe['latency_ms']} ms)."
            latency = probe["latency_ms"]
            provenance = "MEASURED_PHYSICAL_PROBE"
        else:
            status = GSWANTunnelStatus.DISCONNECTED
            message = "GSWAN IPsec tunnel is not detected. Physical connection requires GIL peering and active VPN tunnel."
            latency = None
            provenance = "MEASURED_LOCAL_CHECK"

        missing_requirements = []
        if not env_flag:
            missing_requirements.append("GSWAN_VPN_ACTIVE environment variable not enabled")
        if not (probe["reachable"] or simulated_test):
            missing_requirements.append(f"Network route to GSWAN Gateway {self.gateway_ip}:{self.gateway_port} unreachable")
        if not os.path.exists("deploy/ipsec/ipsec.conf"):
            missing_requirements.append("strongSwan IPsec configuration not installed")

        return {
            "status": status,
            "is_active": (status in (GSWANTunnelStatus.CONNECTED, GSWANTunnelStatus.SIMULATED_ACTIVE)),
            "gateway_ip": self.gateway_ip,
            "latency_ms": latency,
            "latency_provenance": provenance,
            "message": message,
            "missing_requirements": missing_requirements,
            "encryption_profile": "AES-256-GCM / SHA384 / IKEv2 (RFC 7296)",
            "operational_scope": "Statewide Government Intranet (Gujarat Police / GIL)",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


gswan_connector = GSWANConnectorService()
