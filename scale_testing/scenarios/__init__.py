"""
Scale testing scenarios package.
"""
from scale_testing.scenarios.mode1_connection_stress import run_mode1_connection_stress
from scale_testing.scenarios.mode2_metadata_throughput import run_mode2_metadata_throughput
from scale_testing.scenarios.mode3_frame_replay import run_mode3_frame_replay
from scale_testing.scenarios.mode4_mixed_inference import run_mode4_mixed_inference
from scale_testing.scenarios.mode5_failure_recovery import run_mode5_failure_recovery

__all__ = [
    "run_mode1_connection_stress",
    "run_mode2_metadata_throughput",
    "run_mode3_frame_replay",
    "run_mode4_mixed_inference",
    "run_mode5_failure_recovery"
]
