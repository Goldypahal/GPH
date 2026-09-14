"""
High-Precision Telemetry & Latency Metrics Collector for GIVIN Scale Testing.
Measures:
- Events per second (MPS), Frames per second (FPS), Heartbeats per second (HPS)
- Latency percentiles: p50, p90, p95, p99, mean, max
- Host resources: CPU %, RAM (MB/GB), GPU VRAM allocation (if CUDA)
- Queue depth, dropped messages, packet loss percentage
"""

import time
import psutil
from typing import Dict, Any, List, Optional


class ScaleMetricsCollector:
    """Collects and aggregates performance telemetry during scale benchmark runs."""

    def __init__(self, name: str = "scale_benchmark"):
        self.name = name
        self.latencies_ms: List[float] = []
        self.t0: float = time.perf_counter()
        self.total_processed: int = 0
        self.total_failed: int = 0
        self.queue_depths: List[int] = []

    def start(self) -> None:
        """Resets timers and begins collection."""
        self.latencies_ms.clear()
        self.queue_depths.clear()
        self.total_processed = 0
        self.total_failed = 0
        self.t0 = time.perf_counter()

    def record_latency(self, latency_ms: float) -> None:
        """Records a single operation latency measurement."""
        self.latencies_ms.append(latency_ms)
        self.total_processed += 1

    def record_batch(self, count: int, duration_sec: float, queue_depth: int = 0) -> None:
        """Records a processed batch with elapsed time."""
        self.total_processed += count
        if count > 0:
            avg_per_item_ms = (duration_sec * 1000.0) / count
            for _ in range(min(count, 50)):  # Store sample points
                self.latencies_ms.append(avg_per_item_ms)
        self.queue_depths.append(queue_depth)

    def record_failure(self, count: int = 1) -> None:
        """Records failed or dropped events."""
        self.total_failed += count

    def get_resource_snapshot(self) -> Dict[str, Any]:
        """Captures live CPU, RAM, and VRAM utilization."""
        cpu = round(psutil.cpu_percent(interval=None), 1)
        mem = psutil.virtual_memory()
        res: Dict[str, Any] = {
            "cpu_percent": cpu,
            "ram_used_mb": round(mem.used / (1024 * 1024), 1),
            "ram_used_gb": round(mem.used / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "gpu_available": False,
            "vram_used_mb": 0.0
        }

        try:
            import torch
            if torch.cuda.is_available():
                res["gpu_available"] = True
                res["gpu_name"] = torch.cuda.get_device_name(0)
                res["vram_used_mb"] = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1)
                res["vram_total_mb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 1)
        except Exception:
            pass

        return res

    def compute_summary(self) -> Dict[str, Any]:
        """Computes summary statistics, throughput, and latency percentiles."""
        elapsed_sec = max(0.0001, time.perf_counter() - self.t0)
        throughput = round(self.total_processed / elapsed_sec, 1)

        if self.latencies_ms:
            sorted_lat = sorted(self.latencies_ms)
            n = len(sorted_lat)
            p50 = round(sorted_lat[int(n * 0.50)], 2)
            p90 = round(sorted_lat[int(n * 0.90)], 2)
            p95 = round(sorted_lat[min(n - 1, int(n * 0.95))], 2)
            p99 = round(sorted_lat[min(n - 1, int(n * 0.99))], 2)
            mean_lat = round(sum(sorted_lat) / float(n), 2)
            max_lat = round(sorted_lat[-1], 2)
        else:
            p50 = p90 = p95 = p99 = mean_lat = max_lat = 0.0

        avg_queue = round(sum(self.queue_depths) / max(1, len(self.queue_depths)), 1) if self.queue_depths else 0
        loss_pct = round((self.total_failed / max(1, self.total_processed + self.total_failed)) * 100.0, 3)

        resources = self.get_resource_snapshot()

        return {
            "name": self.name,
            "duration_sec": round(elapsed_sec, 3),
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "throughput_per_sec": throughput,
            "packet_loss_pct": loss_pct,
            "latency_p50_ms": p50,
            "latency_p90_ms": p90,
            "latency_p95_ms": p95,
            "latency_p99_ms": p99,
            "latency_mean_ms": mean_lat,
            "latency_max_ms": max_lat,
            "average_queue_depth": avg_queue,
            "resources": resources
        }
