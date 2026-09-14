"""
High-Capacity Virtual Camera Connection Pool & Session Manager.
Simulates up to 80,000 persistent camera sessions across Gujarat's 33 districts:
- Lightweight state machines (O(1) memory overhead per connection)
- Heartbeat pacing (0.1 - 1.0 Hz)
- Connection churn, packet loss, and offline/reconnect simulation
- Millisecond-precision telemetry tracking
"""

import time
import random
from typing import Dict, Any, List, Optional
from scale_testing.generators.camera_generator import CameraGenerator


class CameraSessionState:
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    RECONNECTING = "RECONNECTING"


class VirtualCameraConnectionPool:
    """Manages up to 80,000 persistent virtual camera clients."""

    def __init__(self, target_capacity: int = 80000):
        self.target_capacity = target_capacity
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.last_heartbeat_time: float = 0.0
        self._total_heartbeats = 0
        self._total_reconnects = 0
        self._total_drops = 0

    def initialize_fleet(self, count: Optional[int] = None) -> int:
        """Initializes virtual camera clients from district fleet generator."""
        limit = count or self.target_capacity
        t0 = time.perf_counter()

        self.sessions.clear()
        for cam in CameraGenerator.iter_fleet(limit=limit):
            self.sessions[cam["camera_id"]] = {
                "district": cam["district"],
                "district_code": cam["district_code"],
                "state": CameraSessionState.CONNECTED,
                "resolution": cam["resolution"],
                "codec": cam["codec"],
                "fps": cam["fps"],
                "last_pts": time.time() * 1000.0,
                "packet_loss_pct": 0.0,
                "reconnect_attempts": 0,
                "consecutive_success": 1
            }

        elapsed = time.perf_counter() - t0
        return len(self.sessions)

    def dispatch_heartbeats(self, sample_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Simulates heartbeat delivery across connected cameras.
        Returns latency and success metrics.
        """
        t0 = time.perf_counter()
        targets = list(self.sessions.items())
        if sample_size and sample_size < len(targets):
            targets = random.sample(targets, sample_size)

        success = 0
        failed = 0
        latencies_ms = []

        now_ms = time.time() * 1000.0
        for cam_id, sess in targets:
            if sess["state"] == CameraSessionState.OFFLINE:
                failed += 1
                continue

            # Simulate network jitter (0.2ms - 3.5ms across GSWAN edge subnets)
            base_lat = 0.5 if sess["state"] == CameraSessionState.CONNECTED else 8.5
            jitter = random.random() * 1.5
            lat = round(base_lat + jitter, 2)
            latencies_ms.append(lat)

            sess["last_pts"] = now_ms
            sess["consecutive_success"] += 1
            success += 1
            self._total_heartbeats += 1

        duration_sec = time.perf_counter() - t0
        avg_lat = round(sum(latencies_ms) / max(1, len(latencies_ms)), 2)

        return {
            "dispatched": len(targets),
            "accepted": success,
            "failed": failed,
            "duration_sec": round(duration_sec, 4),
            "throughput_hps": round(success / max(0.001, duration_sec), 1),
            "mean_latency_ms": avg_lat,
            "p95_latency_ms": round(sorted(latencies_ms)[int(len(latencies_ms) * 0.95)], 2) if latencies_ms else 0.0
        }

    def simulate_packet_loss(self, percentage_cameras: float = 0.05, loss_rate: float = 0.15) -> int:
        """Injects network degradation / packet loss into a subset of cameras."""
        count = int(len(self.sessions) * percentage_cameras)
        keys = random.sample(list(self.sessions.keys()), min(count, len(self.sessions)))
        for k in keys:
            self.sessions[k]["state"] = CameraSessionState.DEGRADED
            self.sessions[k]["packet_loss_pct"] = loss_rate
        return len(keys)

    def simulate_offline_drop(self, percentage_cameras: float = 0.05) -> int:
        """Simulates simultaneous link loss (e.g. power cut / fiber drop)."""
        count = int(len(self.sessions) * percentage_cameras)
        keys = random.sample(list(self.sessions.keys()), min(count, len(self.sessions)))
        for k in keys:
            self.sessions[k]["state"] = CameraSessionState.OFFLINE
            self.sessions[k]["consecutive_success"] = 0
            self._total_drops += 1
        return len(keys)

    def simulate_reconnection_storm(self, percentage_cameras: float = 0.10) -> Dict[str, Any]:
        """Simulates thundering-herd reconnection of offline / degraded cameras."""
        t0 = time.perf_counter()
        offline_keys = [k for k, v in self.sessions.items() if v["state"] in (CameraSessionState.OFFLINE, CameraSessionState.DEGRADED)]
        target_count = min(len(offline_keys), int(len(self.sessions) * percentage_cameras))

        reconnected = 0
        reconnect_keys = random.sample(offline_keys, target_count) if offline_keys and target_count > 0 else []
        for k in reconnect_keys:
            self.sessions[k]["state"] = CameraSessionState.CONNECTED
            self.sessions[k]["packet_loss_pct"] = 0.0
            self.sessions[k]["reconnect_attempts"] += 1
            reconnected += 1
            self._total_reconnects += 1

        duration_sec = time.perf_counter() - t0
        return {
            "reconnect_attempted": target_count,
            "reconnect_successful": reconnected,
            "duration_sec": round(duration_sec, 4),
            "reconnect_rate_per_sec": round(reconnected / max(0.001, duration_sec), 1)
        }

    def get_fleet_health_summary(self) -> Dict[str, Any]:
        """Returns snapshot of connection state distribution across the fleet."""
        counts = {
            CameraSessionState.CONNECTED: 0,
            CameraSessionState.DEGRADED: 0,
            CameraSessionState.OFFLINE: 0,
            CameraSessionState.RECONNECTING: 0
        }
        for s in self.sessions.values():
            st = s.get("state", CameraSessionState.CONNECTED)
            counts[st] = counts.get(st, 0) + 1

        total = max(1, len(self.sessions))
        return {
            "total_fleet_size": len(self.sessions),
            "connected_count": counts[CameraSessionState.CONNECTED],
            "degraded_count": counts[CameraSessionState.DEGRADED],
            "offline_count": counts[CameraSessionState.OFFLINE],
            "online_percentage": round((counts[CameraSessionState.CONNECTED] / total) * 100.0, 1),
            "total_lifetime_heartbeats": self._total_heartbeats,
            "total_drops_injected": self._total_drops,
            "total_reconnects_recovered": self._total_reconnects
        }
