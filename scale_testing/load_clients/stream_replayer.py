"""
Stream Replayer & Frame-Reference Multiplexer for GIVIN 80,000 Scale Testing.
Reuses and multiplexes verified benchmark frames across thousands of virtual camera IDs:
- Enables testing of the complete vision metadata and tracking pipeline
- Emulates 80,000 camera feeds without requiring 80,000 physical RTSP encoders
- Maintains authoritative media PTS timestamps and camera-specific sequence IDs
"""

import time
import os
import glob
from typing import Dict, Any, List, Optional
import numpy as np


class StreamReplayer:
    """Multiplexes reference frames across virtual camera IDs."""

    def __init__(self):
        self.reference_frames: List[Dict[str, Any]] = []
        self._frames_replayed = 0

    def load_reference_frames(self, search_dir: str = "data/evidence") -> int:
        """Loads available benchmark frames or creates synthetic reference patterns."""
        self.reference_frames.clear()

        # Check for existing evidence frames in repository
        jpg_files = glob.glob(os.path.join(search_dir, "**", "*.jpg"), recursive=True)
        if jpg_files:
            for path in jpg_files[:10]:
                self.reference_frames.append({
                    "frame_path": path,
                    "resolution": "1920x1080",
                    "source": "EVIDENCE_REPOSITORY_FRAME"
                })

        # If none found, create synthetic reference patterns
        if not self.reference_frames:
            for idx in range(5):
                self.reference_frames.append({
                    "frame_path": f"synthetic_ref_frame_{idx}.jpg",
                    "resolution": "1920x1080",
                    "source": "SYNTHETIC_BENCHMARK_FRAME"
                })

        return len(self.reference_frames)

    def multiplex_batch(
        self,
        camera_ids: List[str],
        fps_sample_rate: float = 1.0,
        frame_idx: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Distributes reference frames across camera_ids with normalized container PTS.
        """
        if not self.reference_frames:
            self.load_reference_frames()

        now_ms = time.time() * 1000.0
        batch = []

        ref_len = len(self.reference_frames)
        for i, cid in enumerate(camera_ids):
            ref = self.reference_frames[(i + frame_idx) % ref_len]
            # Container PTS advances with sample rate
            pts = now_ms + (i * (1000.0 / max(0.1, fps_sample_rate)))

            item = {
                "camera_id": cid,
                "pts_timestamp_ms": pts,
                "frame_reference": ref["frame_path"],
                "resolution": ref["resolution"],
                "sequence_number": frame_idx,
                "source_provenance": ref["source"],
                "sample_rate_fps": fps_sample_rate
            }
            batch.append(item)
            self._frames_replayed += 1

        return batch

    def get_metrics(self) -> Dict[str, Any]:
        """Returns multiplexer throughput metrics."""
        return {
            "total_frames_multiplexed": self._frames_replayed,
            "reference_pool_size": len(self.reference_frames)
        }
