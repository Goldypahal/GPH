from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class DepartmentBase(BaseModel):
    name: str
    code: str
    category: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

class DepartmentOut(DepartmentBase):
    id: str
    created_at: datetime
    class Config:
        from_attributes = True

class CameraBase(BaseModel):
    name: str
    logical_camera_id: str
    department_id: str
    district: str
    location_name: str
    lat: float
    lng: float
    altitude: Optional[float] = 15.0
    fov_angle: Optional[float] = 90.0
    fov_range_m: Optional[float] = 80.0
    vendor: Optional[str] = "Hikvision"
    model: Optional[str] = "DS-2CD2043G2-I"
    camera_type: Optional[str] = "IP Bullet"
    resolution: Optional[str] = "1080p"
    fps: Optional[int] = 25
    protocol: Optional[str] = "RTSP"
    stream_url: Optional[str] = None
    vms_type: Optional[str] = "Milestone"
    storage_type: Optional[str] = "Local NVR"
    retention_days: Optional[int] = 15
    status: Optional[str] = "ACTIVE"

class CameraOut(CameraBase):
    id: str
    created_at: datetime
    health_status: Optional[str] = "ONLINE"
    latency_ms: Optional[int] = 45
    department_name: Optional[str] = None
    class Config:
        from_attributes = True

class VehicleSightingOut(BaseModel):
    id: str
    plate_text: str
    normalized_plate: str
    camera_id: str
    camera_name: Optional[str] = None
    district: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    location_name: Optional[str] = None
    timestamp: datetime
    confidence: float
    vehicle_type: str
    vehicle_color: str
    speed_kmh: float
    direction: str
    evidence_uri: Optional[str] = None
    evidence_hash: Optional[str] = None
    class Config:
        from_attributes = True

class WatchlistCreate(BaseModel):
    list_name: str = "Stolen Vehicles Registry"
    entity_type: str = "VEHICLE"
    vehicle_number: str
    owner_name: Optional[str] = None
    vehicle_make_model: Optional[str] = "Maruti Suzuki Swift"
    vehicle_color: Optional[str] = "Red"
    risk_level: str = "HIGH"
    reason: str = "Reported Stolen under IPC 379"
    case_fir_number: str = "FIR-2026/01"
    registered_authority: str = "Gujarat Police / eGujCop"

class WatchlistOut(WatchlistCreate):
    id: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class AlertOut(BaseModel):
    id: str
    alert_uid: str
    watchlist_id: Optional[str] = None
    sighting_id: str
    camera_id: str
    camera_name: Optional[str] = None
    district: Optional[str] = None
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    plate_text: str
    vehicle_type: Optional[str] = "Car"
    vehicle_color: Optional[str] = "Red"
    risk_level: str
    status: str
    remarks: Optional[str] = None
    dispatched_unit: Optional[str] = None
    acknowledged_by: Optional[str] = None
    created_at: datetime
    evidence_uri: Optional[str] = None
    class Config:
        from_attributes = True

class AlertAction(BaseModel):
    status: str
    remarks: Optional[str] = None
    dispatched_unit: Optional[str] = None
    operator_name: Optional[str] = "Inspector V. Patel (Control Room 1)"

class VehicleTrajectoryPoint(BaseModel):
    sequence: int
    camera_id: str
    camera_name: str
    district: str
    location_name: str
    lat: float
    lng: float
    timestamp: datetime
    speed_kmh: float
    confidence: float
    time_delta_mins: Optional[float] = None
    distance_km: Optional[float] = None
    evidence_uri: Optional[str] = None
    match_method: Optional[str] = "PLATE_EXACT" # "PLATE_EXACT" | "PLATE_FUZZY" | "VISUAL_REID"
    link_status: Optional[str] = "VERIFIED_PLAUSIBLE" # "VERIFIED_PLAUSIBLE" | "LOW_CONFIDENCE_LINK" | "IMPOSSIBLE_SPEED"
    implied_speed_kmh: Optional[float] = None

class VehicleJourneySummary(BaseModel):
    plate_number: str
    total_sightings: int
    first_seen: datetime
    last_seen: datetime
    districts_traversed: List[str]
    total_estimated_distance_km: float
    average_speed_kmh: float
    trajectory: List[VehicleTrajectoryPoint]
    matched_watchlist: Optional[WatchlistOut] = None
    route_confidence_pct: Optional[float] = 94.0
    route_status: Optional[str] = "VERIFIED_CONTINUOUS" # "VERIFIED_CONTINUOUS" | "FLAGGED_ANOMALY"

class LivePursuitPosition(BaseModel):
    plate_number: str
    status: str  # "LIVE_PREDICTED" | "STALE" | "AT_CAMERA"
    lat: float
    lng: float
    heading_deg: float
    speed_kmh: float
    last_confirmed_camera: str
    last_confirmed_district: str
    last_confirmed_time: datetime
    seconds_since_confirmed: float
    predicted_next_camera: Optional[str] = None
    predicted_next_district: Optional[str] = None
    predicted_next_lat: Optional[float] = None
    predicted_next_lng: Optional[float] = None
    eta_to_next_camera_sec: Optional[float] = None
    trail: List[List[float]] = []
    risk_level: Optional[str] = None
    watchlist_reason: Optional[str] = None

class ScaleCapacitySimulation(BaseModel):
    camera_count: int
    resolution: str
    fps: int
    retention_days: int
    central_model4_bandwidth_gbps: float
    hybrid_model_bandwidth_gbps: float
    bandwidth_savings_percentage: float
    central_storage_petabytes: float
    hybrid_edge_storage_petabytes: float
    central_gpu_servers_needed: int
    hybrid_edge_nodes_needed: int
    estimated_annual_cost_savings_inr_crores: float
