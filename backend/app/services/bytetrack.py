import math
from enum import Enum
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

class TrackState(Enum):
    NEW = 0
    TRACKED = 1
    LOST = 2
    REMOVED = 3

def calculate_iou(boxA: list[float], boxB: list[float]) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_width = max(0.0, xB - xA)
    inter_height = max(0.0, yB - yA)
    inter_area = inter_width * inter_height

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    union_area = boxA_area + boxB_area - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area

class STrack:
    """Single Object Track state with authoritative PTS kinematics."""
    _count = 0

    def __init__(self, bbox: list[float], score: float, class_name: str = "Car"):
        STrack._count += 1
        self.track_id = STrack._count
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.score = score
        self.class_name = class_name
        self.state = TrackState.NEW
        self.frame_id = 0
        self.tracklet_len = 0
        self.time_since_update = 0
        self.pts: Optional[float] = None
        self.pts_delta: float = 0.04
        self.speed_px_per_sec: float = 0.0

        # PTS-normalized velocity vector (px/sec)
        self.velocity = [0.0, 0.0]

    def update(self, new_track: "STrack", frame_id: int, pts: Optional[float] = None, pts_delta: Optional[float] = None):
        self.frame_id = frame_id
        self.tracklet_len += 1
        self.pts = pts
        dt = pts_delta if (pts_delta and pts_delta > 0) else 0.04
        self.pts_delta = dt
        
        # Estimate velocity using authoritative PTS delta, NOT arrival time
        old_cx = (self.bbox[0] + self.bbox[2]) / 2.0
        old_cy = (self.bbox[1] + self.bbox[3]) / 2.0
        new_cx = (new_track.bbox[0] + new_track.bbox[2]) / 2.0
        new_cy = (new_track.bbox[1] + new_track.bbox[3]) / 2.0

        # Velocity in pixels per second: displacement / actual_pts_delta
        self.velocity = [(new_cx - old_cx) / dt, (new_cy - old_cy) / dt]
        self.speed_px_per_sec = math.hypot(self.velocity[0], self.velocity[1])

        self.bbox = new_track.bbox
        self.score = new_track.score
        self.state = TrackState.TRACKED
        self.time_since_update = 0

    def predict(self, dt: float = 0.04):
        """Linearly projects bounding box based on velocity and PTS delta."""
        dx = self.velocity[0] * dt
        dy = self.velocity[1] * dt
        self.bbox = [
            self.bbox[0] + dx,
            self.bbox[1] + dy,
            self.bbox[2] + dx,
            self.bbox[3] + dy
        ]
        self.time_since_update += 1

    def mark_lost(self):
        self.state = TrackState.LOST

    def mark_removed(self):
        self.state = TrackState.REMOVED

class ByteTracker:
    """
    ByteTrack single camera tracker instance.
    Associates high-confidence detections first, then recovers low-confidence
    detections to prevent track fragmentation through occlusions.
    """

    def __init__(self, high_thresh: float = 0.5, low_thresh: float = 0.1, match_thresh: float = 0.7, max_lost_frames: int = 30):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_thresh = match_thresh
        self.max_lost_frames = max_lost_frames
        
        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []
        self.frame_id = 0
        self.last_pts: Optional[float] = None

    def reset(self):
        """Resets all tracking states for this camera upon scene discontinuity / loop."""
        self.tracked_stracks.clear()
        self.lost_stracks.clear()
        self.removed_stracks.clear()
        self.last_pts = None

    def update(
        self,
        detections: List[Tuple[list[float], float, str]],
        pts: Optional[float] = None,
        pts_delta: Optional[float] = None
    ) -> List[STrack]:
        """
        Input: list of (bbox, score, class_name)
        Returns active tracked STracks for the current frame.
        Uses authoritative PTS delta for kinematic prediction and displacement.
        """
        # Section 39.9: Scene loop boundary or severe temporal gap triggers clean state reset
        if pts is not None and self.last_pts is not None and pts < self.last_pts:
            self.reset()
        elif pts_delta is not None and pts_delta > 5.0:
            self.reset()

        dt = pts_delta if (pts_delta and pts_delta > 0) else (
            max(0.001, pts - self.last_pts) if (pts is not None and self.last_pts is not None) else 0.04
        )
        self.last_pts = pts

        self.frame_id += 1
        activated_stracks: List[STrack] = []
        refind_stracks: List[STrack] = []

        # Predict current locations of existing tracks using actual PTS delta
        for strack in self.tracked_stracks:
            strack.predict(dt)
        for strack in self.lost_stracks:
            strack.predict(dt)

        # Partition detections into high and low confidence pools
        high_dets: List[STrack] = []
        low_dets: List[STrack] = []
        for bbox, score, cls in detections:
            s = STrack(bbox, score, cls)
            if score >= self.high_thresh:
                high_dets.append(s)
            elif score >= self.low_thresh:
                low_dets.append(s)

        # Pool 1: Match high-confidence detections with existing tracks
        tracked_pool = [t for t in self.tracked_stracks if t.state == TrackState.TRACKED]
        dists_1 = np.zeros((len(tracked_pool), len(high_dets)), dtype=float)
        for i, t in enumerate(tracked_pool):
            for j, d in enumerate(high_dets):
                dists_1[i, j] = 1.0 - calculate_iou(t.bbox, d.bbox)

        matched_tracks_1, unmatched_tracks_1, unmatched_dets_1 = self._linear_assignment(dists_1, tracked_pool, high_dets, self.match_thresh)

        for t_idx, d_idx in matched_tracks_1:
            track = tracked_pool[t_idx]
            det = high_dets[d_idx]
            track.update(det, self.frame_id, pts, dt)
            activated_stracks.append(track)

        # Pool 2: Match low-confidence detections with unmatched tracks
        remain_tracks = [tracked_pool[i] for i in unmatched_tracks_1]
        dists_2 = np.zeros((len(remain_tracks), len(low_dets)), dtype=float)
        for i, t in enumerate(remain_tracks):
            for j, d in enumerate(low_dets):
                dists_2[i, j] = 1.0 - calculate_iou(t.bbox, d.bbox)

        matched_tracks_2, unmatched_tracks_2, _ = self._linear_assignment(dists_2, remain_tracks, low_dets, 0.5)

        for t_idx, d_idx in matched_tracks_2:
            track = remain_tracks[t_idx]
            det = low_dets[d_idx]
            track.update(det, self.frame_id, pts, dt)
            activated_stracks.append(track)

        for t_idx in unmatched_tracks_2:
            track = remain_tracks[t_idx]
            track.mark_lost()
            self.lost_stracks.append(track)

        # Pool 3: Initialize new tracks for unmatched high-confidence detections
        for d_idx in unmatched_dets_1:
            det = high_dets[d_idx]
            det.state = TrackState.TRACKED
            det.frame_id = self.frame_id
            det.tracklet_len = 1
            det.pts = pts
            det.pts_delta = dt
            activated_stracks.append(det)

        # Clean up lost tracks exceeding max age
        still_lost = []
        for t in self.lost_stracks:
            if (self.frame_id - t.frame_id) > self.max_lost_frames:
                t.mark_removed()
                self.removed_stracks.append(t)
            else:
                still_lost.append(t)
        self.lost_stracks = still_lost

        # Update active tracked pool
        self.tracked_stracks = activated_stracks
        return [t for t in self.tracked_stracks if t.state == TrackState.TRACKED]

    @staticmethod
    def _linear_assignment(dists: np.ndarray, tracks: list, dets: list, thresh: float):
        if dists.size == 0:
            return [], list(range(len(tracks))), list(range(len(dets)))

        matched = []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_dets = list(range(len(dets)))

        # Greedy matching by minimum distance (IoU cost)
        while len(unmatched_tracks) > 0 and len(unmatched_dets) > 0:
            min_val = np.min(dists[unmatched_tracks][:, unmatched_dets])
            if min_val > thresh:
                break
            # Find indices
            r, c = np.where(dists == min_val)
            for ri, ci in zip(r, c):
                if ri in unmatched_tracks and ci in unmatched_dets:
                    matched.append((ri, ci))
                    unmatched_tracks.remove(ri)
                    unmatched_dets.remove(ci)
                    break

        return matched, unmatched_tracks, unmatched_dets

class TrackerPool:
    """Manages dedicated ByteTracker instances per camera stream."""
    _trackers: Dict[str, ByteTracker] = {}

    @classmethod
    def get_tracker(cls, camera_id: str) -> ByteTracker:
        if camera_id not in cls._trackers:
            cls._trackers[camera_id] = ByteTracker()
        return cls._trackers[camera_id]

    @classmethod
    def reset_camera(cls, camera_id: str):
        """Resets tracker for a single camera (e.g. on scene discontinuity)."""
        if camera_id in cls._trackers:
            cls._trackers[camera_id].reset()

    @classmethod
    def reset(cls):
        cls._trackers.clear()
        STrack._count = 0
