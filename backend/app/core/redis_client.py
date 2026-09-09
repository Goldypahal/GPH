import time
import json
import threading
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings

class RedisStateClient:
    """
    Production-grade distributed state layer backed by Redis.
    Provides temporal OCR fusion buffering, watchlist caching, and ByteTrack state persistence.
    Includes a thread-safe in-memory fallback for offline/development environments.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis = None
        self._is_connected = False
        self._fallback_store: Dict[str, Any] = {}
        self._fallback_ttls: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._connect()

    def _connect(self):
        try:
            import redis
            client = redis.Redis.from_url(
                self.redis_url,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                decode_responses=True
            )
            client.ping()
            self._redis = client
            self._is_connected = True
        except Exception:
            self._redis = None
            self._is_connected = False

    def health_check(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if self._redis:
            try:
                self._redis.ping()
                latency = round((time.perf_counter() - start) * 1000.0, 2)
                return {
                    "status": "READY",
                    "driver": "REDIS_CLUSTER_READY",
                    "url": self.redis_url,
                    "latency_ms": latency
                }
            except Exception as e:
                self._is_connected = False
                return {
                    "status": "FALLBACK_IN_MEMORY",
                    "driver": "IN_MEMORY_FALLBACK",
                    "warning": f"Redis ping failed: {e}"
                }
        return {
            "status": "FALLBACK_IN_MEMORY",
            "driver": "IN_MEMORY_FALLBACK",
            "note": "Running in-memory local state cache"
        }

    # =========================================================================
    # Watchlist High-Speed Cache
    # =========================================================================

    def cache_watchlist_entry(self, plate: str, data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        key = f"watchlist:{plate.upper()}"
        val = json.dumps(data)
        if self._is_connected and self._redis:
            try:
                self._redis.setex(key, ttl_seconds, val)
            except Exception:
                pass
        with self._lock:
            self._fallback_store[key] = val
            self._fallback_ttls[key] = time.time() + ttl_seconds
        return True

    def get_cached_watchlist_entry(self, plate: str) -> Optional[Dict[str, Any]]:
        key = f"watchlist:{plate.upper()}"
        if self._is_connected and self._redis:
            try:
                raw = self._redis.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        with self._lock:
            if key in self._fallback_store:
                if time.time() <= self._fallback_ttls.get(key, float("inf")):
                    return json.loads(self._fallback_store[key])
                else:
                    del self._fallback_store[key]
                    if key in self._fallback_ttls:
                        del self._fallback_ttls[key]
        return None

    # =========================================================================
    # Temporal OCR Fusion Buffer (plate_fusion:{camera_id}:{track_id})
    # =========================================================================

    def record_track_ocr_sample(
        self,
        camera_id: str,
        track_id: int,
        plate: str,
        confidence: float,
        ttl_seconds: int = 30
    ) -> None:
        """Appends an OCR sample to the track's temporal buffer."""
        key = f"plate_fusion:{camera_id}:{track_id}"
        sample = json.dumps({"plate": plate, "confidence": confidence, "ts": time.time()})
        if self._is_connected and self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.rpush(key, sample)
                pipe.expire(key, ttl_seconds)
                pipe.execute()
                return
            except Exception:
                pass
        with self._lock:
            if key not in self._fallback_store:
                self._fallback_store[key] = []
            self._fallback_store[key].append(sample)
            self._fallback_ttls[key] = time.time() + ttl_seconds

    def get_track_ocr_samples(self, camera_id: str, track_id: int) -> List[Dict[str, Any]]:
        """Retrieves all temporal OCR samples collected for this track window."""
        key = f"plate_fusion:{camera_id}:{track_id}"
        if self._is_connected and self._redis:
            try:
                items = self._redis.lrange(key, 0, -1)
                return [json.loads(i) for i in items]
            except Exception:
                pass
        with self._lock:
            if key in self._fallback_store:
                if time.time() <= self._fallback_ttls.get(key, float("inf")):
                    return [json.loads(i) for i in self._fallback_store[key]]
                else:
                    del self._fallback_store[key]
                    if key in self._fallback_ttls:
                        del self._fallback_ttls[key]
        return []

    # =========================================================================
    # Tracking State
    # =========================================================================

    def set_track_state(self, camera_id: str, track_id: int, state: Dict[str, Any], ttl: int = 60) -> None:
        key = f"track:{camera_id}:{track_id}"
        val = json.dumps(state)
        if self._is_connected and self._redis:
            try:
                self._redis.setex(key, ttl, val)
                return
            except Exception:
                pass
        with self._lock:
            self._fallback_store[key] = val
            self._fallback_ttls[key] = time.time() + ttl

    def get_track_state(self, camera_id: str, track_id: int) -> Optional[Dict[str, Any]]:
        key = f"track:{camera_id}:{track_id}"
        if self._is_connected and self._redis:
            try:
                raw = self._redis.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        with self._lock:
            if key in self._fallback_store:
                if time.time() <= self._fallback_ttls.get(key, float("inf")):
                    return json.loads(self._fallback_store[key])
    # =========================================================================
    # Generic Key-Value Cache Interface
    # =========================================================================

    def get(self, key: str) -> Optional[str]:
        """Generic get for string values."""
        if self._is_connected and self._redis:
            try:
                val = self._redis.get(key)
                if val is not None:
                    return val if isinstance(val, str) else val.decode("utf-8")
            except Exception:
                pass
        with self._lock:
            if key in self._fallback_store:
                if time.time() <= self._fallback_ttls.get(key, float("inf")):
                    return self._fallback_store[key]
                else:
                    del self._fallback_store[key]
                    if key in self._fallback_ttls:
                        del self._fallback_ttls[key]
        return None

    def set(self, key: str, value: str, ttl_seconds: int = 3600) -> bool:
        """Generic set with TTL in seconds."""
        if self._is_connected and self._redis:
            try:
                self._redis.set(key, value, ex=ttl_seconds)
                return True
            except Exception:
                pass
        with self._lock:
            self._fallback_store[key] = value
            self._fallback_ttls[key] = time.time() + ttl_seconds
        return True

# Singleton client
redis_state = RedisStateClient()

