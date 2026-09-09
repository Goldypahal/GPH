"""
Redis-Backed Temporal OCR Fusion Engine.
Buffers OCR readings across consecutive video frames for a persistent ByteTrack ID (e.g. Track 17)
and performs character-positional weighted consensus voting to eliminate optical flicker.
"""

from collections import defaultdict, Counter
from typing import Tuple, List, Dict, Any
from backend.app.core.redis_client import redis_state
from backend.app.services.anpr_engine import ANPREngine

class TemporalOCRFusion:
    """
    Performs multi-frame temporal voting on OCR readings for a specific vehicle track.
    Resolves flickering characters (e.g. '8' vs 'B', '0' vs 'O') by leveraging temporal redundancy.
    """

    def __init__(self, window_size: int = 10, ttl_seconds: int = 30):
        self.window_size = window_size
        self.ttl_seconds = ttl_seconds

    def add_sample_and_fuse(
        self,
        camera_id: str,
        track_id: int,
        raw_plate: str,
        confidence: float
    ) -> Tuple[str, float, int]:
        """
        Records a single frame OCR observation and returns the current consensus fused plate.
        Returns: (fused_plate, fused_confidence, total_frame_votes)
        """
        cleaned = ANPREngine.normalize_plate(raw_plate)
        if not cleaned:
            return raw_plate, confidence, 1

        # 1. Record sample to Redis distributed state
        redis_state.record_track_ocr_sample(
            camera_id=camera_id,
            track_id=track_id,
            plate=cleaned,
            confidence=confidence,
            ttl_seconds=self.ttl_seconds
        )

        # 2. Fetch history of samples for this track
        samples = redis_state.get_track_ocr_samples(camera_id, track_id)
        if not samples or len(samples) <= 1:
            corrected, fmt_conf, _ = ANPREngine.validate_and_correct(cleaned)
            return corrected, max(confidence, fmt_conf), 1

        # Limit to sliding window size
        recent_samples = samples[-self.window_size:]
        vote_count = len(recent_samples)

        # 3. Positional character consensus voting
        # Find modal string length (e.g. 10 chars for GJ01AB1234)
        lengths = [len(s["plate"]) for s in recent_samples if s.get("plate")]
        if not lengths:
            return cleaned, confidence, 1
        modal_len = Counter(lengths).most_common(1)[0][0]

        # Filter samples that match the modal length
        valid_samples = [s for s in recent_samples if len(s.get("plate", "")) == modal_len]
        if not valid_samples:
            valid_samples = recent_samples

        consensus_chars = []
        for pos in range(modal_len):
            char_weights: Dict[str, float] = defaultdict(float)
            for s in valid_samples:
                plate_str = s.get("plate", "")
                if pos < len(plate_str):
                    char = plate_str[pos]
                    conf = float(s.get("confidence", 0.5))
                    # Prioritize valid characters (e.g. letters in positions 0,1, digits in 2,3)
                    weight_multiplier = 1.0
                    if pos in (0, 1) and char.isalpha():
                        weight_multiplier = 1.25
                    elif pos in (2, 3) and char.isdigit():
                        weight_multiplier = 1.25
                    elif pos >= (modal_len - 4) and char.isdigit():
                        weight_multiplier = 1.25

                    char_weights[char] += conf * weight_multiplier

            if char_weights:
                best_char = max(char_weights.keys(), key=lambda c: char_weights[c])
                consensus_chars.append(best_char)
            else:
                consensus_chars.append("X")

        fused_raw = "".join(consensus_chars)
        corrected_plate, format_conf, is_valid = ANPREngine.validate_and_correct(fused_raw)

        # Base confidence is average confidence of all samples + corroboration bonus
        avg_conf = sum(s.get("confidence", 0.5) for s in recent_samples) / float(vote_count)
        corroboration_bonus = min(0.08, (vote_count - 1) * 0.02)
        fused_conf = min(0.99, round(max(avg_conf, format_conf) + corroboration_bonus, 3))

        return corrected_plate, fused_conf, vote_count

temporal_fusion_engine = TemporalOCRFusion()
