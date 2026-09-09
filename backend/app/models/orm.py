import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

# =====================================================================
# 1. Organization & Spatial Administrative Boundaries
# =====================================================================

class District(Base):
    __tablename__ = "districts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    state = Column(String(100), default="Gujarat")
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    boundary_geojson = Column(Text, nullable=True) # GeoJSON polygon for PostGIS / GIS layers
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    category = Column(String(100), default="State Government")
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    cameras = relationship("Camera", back_populates="department")

# =====================================================================
# 2. Authentication, RBAC, and ABAC Permissions
# =====================================================================

class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(50), nullable=False, unique=True) # SUPER_ADMIN, INVESTIGATOR, etc.
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=True)

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    code = Column(String(100), nullable=False, unique=True) # camera:read, evidence:export
    resource = Column(String(50), nullable=False)           # camera, evidence, case
    action = Column(String(50), nullable=False)             # read, write, export, delete

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False)
    permission_id = Column(String(36), ForeignKey("permissions.id"), nullable=False)

class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="INVESTIGATOR")
    jurisdiction_district = Column(String(100), nullable=True) # None = Statewide, or "Ahmedabad"
    department_code = Column(String(50), default="HOME_POLICE")
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# =====================================================================
# 3. Camera Registry, Hardware & VMS Federation
# =====================================================================

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False)
    logical_camera_id = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    district = Column(String(100), nullable=False)
    location_name = Column(String(255), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    altitude = Column(Float, default=15.0)
    fov_angle = Column(Float, default=90.0)
    fov_range_m = Column(Float, default=80.0)
    
    vendor = Column(String(100), default="Hikvision")
    model = Column(String(100), default="DS-2CD2043G2-I")
    camera_type = Column(String(50), default="IP Bullet")
    resolution = Column(String(50), default="1080p")
    fps = Column(Integer, default=25)
    
    protocol = Column(String(50), default="RTSP") # RTSP, ONVIF, RTMP, VMS-API
    stream_url = Column(String(500), nullable=True)
    vms_type = Column(String(100), default="Milestone")
    storage_type = Column(String(100), default="Local NVR")
    retention_days = Column(Integer, default=15)
    
    status = Column(String(50), default="ACTIVE") # ACTIVE, DEGRADED, INACTIVE, MAINTENANCE
    is_public_domain = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department = relationship("Department", back_populates="cameras")
    health = relationship("CameraHealth", back_populates="camera", uselist=False)
    sightings = relationship("VehicleSighting", back_populates="camera")
    credentials = relationship("CameraCredential", back_populates="camera", uselist=False)
    configuration = relationship("CameraConfiguration", back_populates="camera", uselist=False)

class CameraCredential(Base):
    __tablename__ = "camera_credentials"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(36), ForeignKey("cameras.id"), unique=True, nullable=False)
    username = Column(String(100), default="admin")
    encrypted_password = Column(String(255), nullable=True)
    auth_type = Column(String(50), default="BASIC") # BASIC, DIGEST, TOKEN
    port = Column(Integer, default=554)

    camera = relationship("Camera", back_populates="credentials")

class CameraConfiguration(Base):
    __tablename__ = "camera_configurations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(36), ForeignKey("cameras.id"), unique=True, nullable=False)
    config_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    camera = relationship("Camera", back_populates="configuration")

class CameraHealth(Base):
    __tablename__ = "camera_health"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(36), ForeignKey("cameras.id"), unique=True, nullable=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    latency_ms = Column(Integer, default=45)
    packet_loss = Column(Float, default=0.2)
    cpu_usage = Column(Float, default=34.5)
    memory_usage = Column(Float, default=52.0)
    clock_drift_ms = Column(Float, default=5.0)
    status = Column(String(50), default="ONLINE")

    camera = relationship("Camera", back_populates="health")

# =====================================================================
# 4. AI Vision Pipeline & Tracking Lineage
# =====================================================================

class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)         # yolo11_vehicle, dedicated_plate_detector, crnn_anpr
    model_type = Column(String(50), nullable=False)   # VEHICLE_DETECTOR, PLATE_DETECTOR, OCR_ENGINE, REID
    version = Column(String(50), nullable=False)
    framework = Column(String(50), default="PyTorch") # PyTorch, ONNX, TensorRT
    weights_uri = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AIModelDeployment(Base):
    __tablename__ = "ai_model_deployments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    model_id = Column(String(36), ForeignKey("ai_models.id"), nullable=False)
    node_identifier = Column(String(100), nullable=False) # edge-node-ahm-01 or central-gpu-01
    status = Column(String(50), default="RUNNING")
    last_heartbeat = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class VehicleTrack(Base):
    __tablename__ = "vehicle_tracks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False)
    track_id = Column(Integer, nullable=False) # ByteTrack / BoT-SORT local tracker ID
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    best_plate = Column(String(50), nullable=True)
    best_confidence = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

class PlateDetection(Base):
    __tablename__ = "plate_detections"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False)
    track_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    plate_text = Column(String(50), nullable=False)
    confidence = Column(Float, default=0.90)
    crop_uri = Column(String(500), nullable=True)
    bbox_json = Column(Text, nullable=True)

class ANPRResult(Base):
    __tablename__ = "anpr_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    plate_detection_id = Column(String(36), ForeignKey("plate_detections.id"), nullable=False)
    raw_ocr_text = Column(String(50), nullable=False)
    normalized_plate = Column(String(50), nullable=False, index=True)
    ocr_confidence = Column(Float, default=0.90)
    optical_corrected = Column(Boolean, default=False)
    ocr_engine = Column(String(50), default="PaddleOCR")

class VehicleSighting(Base):
    __tablename__ = "vehicle_sightings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    plate_text = Column(String(50), nullable=False, index=True)
    normalized_plate = Column(String(50), nullable=False, index=True)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    confidence = Column(Float, default=0.92)
    vehicle_type = Column(String(50), default="Car")
    vehicle_color = Column(String(50), default="White")
    speed_kmh = Column(Float, default=55.0)
    direction = Column(String(50), default="Northbound")
    bbox_json = Column(Text, nullable=True)
    evidence_uri = Column(String(500), nullable=True)
    evidence_hash = Column(String(64), nullable=True)
    
    camera = relationship("Camera", back_populates="sightings")
    alerts = relationship("Alert", back_populates="sighting")
    embeddings = relationship("VehicleEmbedding", back_populates="sighting")

class VehicleEmbedding(Base):
    __tablename__ = "vehicle_embeddings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    sighting_id = Column(String(36), ForeignKey("vehicle_sightings.id"), nullable=False)
    vehicle_crop_hash = Column(String(64), nullable=False)
    embedding_json = Column(Text, nullable=True) # 512-dim Re-ID feature vector (pgvector target)
    model_name = Column(String(100), default="osnet_x1_0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sighting = relationship("VehicleSighting", back_populates="embeddings")

# =====================================================================
# 5. Watchlists, Hotlists & Alerts
# =====================================================================

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    list_name = Column(String(100), default="Stolen Vehicles Registry")
    entity_type = Column(String(50), default="VEHICLE")
    vehicle_number = Column(String(50), nullable=False, index=True)
    owner_name = Column(String(255), nullable=True)
    vehicle_make_model = Column(String(100), nullable=True)
    vehicle_color = Column(String(50), nullable=True)
    risk_level = Column(String(50), default="HIGH")
    reason = Column(Text, nullable=False)
    case_fir_number = Column(String(100), nullable=True)
    registered_authority = Column(String(255), default="Gujarat Police")
    status = Column(String(50), default="ACTIVE")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    alerts = relationship("Alert", back_populates="watchlist")
    entries = relationship("WatchlistEntry", back_populates="watchlist")

class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    watchlist_id = Column(String(36), ForeignKey("watchlists.id"), nullable=False)
    identifier = Column(String(100), nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)
    risk_level = Column(String(50), default="HIGH")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    watchlist = relationship("Watchlist", back_populates="entries")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    alert_uid = Column(String(50), unique=True, nullable=False, index=True)
    watchlist_id = Column(String(36), ForeignKey("watchlists.id"), nullable=True)
    sighting_id = Column(String(36), ForeignKey("vehicle_sightings.id"), nullable=False)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False)
    plate_text = Column(String(50), nullable=False)
    risk_level = Column(String(50), default="HIGH")
    status = Column(String(50), default="NEW") # NEW, ACKNOWLEDGED, DISPATCHED, RESOLVED, DISMISSED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    remarks = Column(Text, nullable=True)
    dispatched_unit = Column(String(100), nullable=True)

    watchlist = relationship("Watchlist", back_populates="alerts")
    sighting = relationship("VehicleSighting", back_populates="alerts")
    camera = relationship("Camera")
    events = relationship("AlertEvent", back_populates="alert")

class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=False)
    event_type = Column(String(50), nullable=False) # ACKNOWLEDGE, DISPATCH, RESOLVE
    actor = Column(String(100), nullable=False)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    alert = relationship("Alert", back_populates="events")

# =====================================================================
# 6. Investigation Cases, Dossiers & Chain of Custody
# =====================================================================

class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    fir_number = Column(String(100), nullable=True)
    status = Column(String(50), default="INVESTIGATING")
    priority = Column(String(50), default="HIGH")
    assigned_investigator = Column(String(255), default="Inspector V. Patel")
    jurisdiction_district = Column(String(100), default="Statewide")
    target_vehicle_plate = Column(String(50), nullable=False, index=True)
    created_from_alert_id = Column(String(36), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    timeline_entries = relationship("CaseTimelineEntry", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")
    assignments = relationship("CaseAssignment", back_populates="case", cascade="all, delete-orphan")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")

class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_role = Column(String(50), default="PRIMARY_INVESTIGATOR")
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="assignments")
    user = relationship("User")

class CaseNote(Base):
    __tablename__ = "case_notes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    author_id = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="notes")

class CaseTimelineEntry(Base):
    __tablename__ = "case_timeline_entries"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    entry_type = Column(String(50), default="NOTE")
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(String(255), default="Inspector V. Patel")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="timeline_entries")

class CaseEvidence(Base):
    __tablename__ = "case_evidence"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    sighting_id = Column(String(36), ForeignKey("vehicle_sightings.id"), nullable=False)
    evidence_hash = Column(String(64), nullable=True)
    sec_65b_cert_ref = Column(String(100), nullable=True)
    attached_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="evidence_items")
    sighting = relationship("VehicleSighting")

# =====================================================================
# 7. Dedicated Evidence Management & Section 65B Chain of Custody
# =====================================================================

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    sighting_id = Column(String(36), ForeignKey("vehicle_sightings.id"), nullable=True)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    frame_hash = Column(String(64), nullable=False)      # SHA-256 raw frame hash
    plate_crop_hash = Column(String(64), nullable=True) # SHA-256 license crop hash
    ocr_confidence = Column(Float, default=0.95)
    model_version = Column(String(50), default="GIVIN-Vision-1.2")
    object_uri = Column(String(500), nullable=False)    # Object storage path
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    access_logs = relationship("EvidenceAccess", back_populates="evidence")

class EvidenceAccess(Base):
    __tablename__ = "evidence_access_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=False)
    user_id = Column(String(100), nullable=False)
    access_type = Column(String(50), nullable=False) # VIEW, DOWNLOAD, EXPORT, SHARE
    ip_address = Column(String(50), nullable=True)
    justification = Column(String(255), nullable=True)
    accessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    evidence = relationship("Evidence", back_populates="access_logs")

class EvidenceExport(Base):
    __tablename__ = "evidence_exports"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    evidence_ids_json = Column(Text, nullable=False)
    exported_by = Column(String(100), nullable=False)
    export_hash = Column(String(64), nullable=False)
    destination = Column(String(255), default="STATE_COURT_PORTAL")
    exported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# =====================================================================
# 8. Cryptographic Audit Log & Chained Tamper Evidence
# =====================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    details_json = Column(Text, nullable=True)
    prev_signature_hash = Column(String(64), nullable=True) # Hash-chain link
    signature_hash = Column(String(64), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    prev_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# =====================================================================
# 9. Government Integrations & System Telemetry
# =====================================================================

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)
    provider_code = Column(String(50), unique=True, nullable=False) # VAHAN, SARATHI, EGUJCOP, AFIS
    base_url = Column(String(500), nullable=False)
    status = Column(String(50), default="ONLINE") # ONLINE, OFFLINE, SANDBOX, MOCK
    is_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    integration_id = Column(String(36), ForeignKey("integrations.id"), nullable=False)
    auth_type = Column(String(50), default="OAUTH2")
    credential_encrypted = Column(Text, nullable=True)

class SystemHealth(Base):
    __tablename__ = "system_health_nodes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    node_id = Column(String(100), unique=True, nullable=False)
    service_name = Column(String(100), nullable=False) # api, edge_worker, ingestion
    status = Column(String(50), default="HEALTHY")
    metrics_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
