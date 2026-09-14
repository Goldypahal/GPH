"""
Mode 3: Frame-Reference Replay Scalability Test.
Evaluates:
- Multiplexing real/reference benchmark frames across 80,000 virtual cameras
- Tests the complete event generation and PTS synchronization pipeline
- Eliminates 80,000 physical video decoder constraints while testing full ingest logic
"""

import time
from typing import Dict, Any, List, Optional
from scale_testing.generators.camera_generator import CameraGenerator
from scale_testing.load_clients.stream_replayer import StreamReplayer
from scale_testing.metrics.collector import ScaleMetricsCollector


def run_mode3_frame_replay(
    virtual_camera_count: int = 80000,
    fps_sample_rate: float = 1.0,
    batches: int = 4
) -> Dict[str, Any]:
    """
    Executes Mode 3 Frame-Reference Replay Test.
    """
    collector = ScaleMetricsCollector(name=f"mode3_frame_replay_{virtual_camera_count}")
    replayer = StreamReplayer()
    replayer.load_reference_frames()

    # Generate camera ID pool
    camera_ids = [c["camera_id"] for c in CameraGenerator.iter_fleet(limit=virtual_camera_count)]
    collector.start()

    chunk_size = 5000
    total_frames = 0
    t0 = time.perf_counter()

    for batch_num in range(batches):
        for idx in range(0, len(camera_ids), chunk_size):
            sub_cams = camera_ids[idx:idx + chunk_size]
            t_chunk_start = time.perf_counter()
            items = replayer.multiplex_batch(
                camera_ids=sub_cams,
                fps_sample_rate=fps_sample_rate,
                frame_idx=batch_num
            )
            duration = time.perf_counter() - t_chunk_start
            collector.record_batch(count=len(items), duration_sec=duration)
            total_frames += len(items)

    elapsed = time.perf_counter() - t0
    summary = collector.compute_summary()

    return {
        "scenario": "MODE_3_FRAME_REFERENCE_REPLAY",
        "virtual_camera_pool": len(camera_ids),
        "target_sample_fps": fps_sample_rate,
        "total_frames_multiplexed": total_frames,
        "elapsed_sec": round(elapsed, 3),
        "multiplex_throughput_fps": summary["throughput_per_sec"],
        "latency_p50_ms": summary["latency_p50_ms"],
        "latency_p95_ms": summary["latency_p95_ms"],
        "latency_p99_ms": summary["latency_p99_ms"],
        "reference_frames_available": len(replayer.reference_frames),
        "system_resources": summary["resources"],
        "verdict": "PASSED" if summary["throughput_per_sec"] > 20000 else "DEGRADED"
    }
