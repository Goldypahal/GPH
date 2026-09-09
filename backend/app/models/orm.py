import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

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
    fov_angle = Column(Float, default=90.0)      # Heading / Azimuth angle in degrees (0-360)
    fov_range_m = Column(Float, default=80.0)    # Coverage reach in meters
    
    # Heterogeneous Hardware & Vendor details
    vendor = Column(String(100), default="Hikvision")  # Dahua, CP Plus, Axis, Honeywell, Hanwha
    model = Column(String(100), default="DS-2CD2043G2-I")
    camera_type = Column(String(50), default="IP Bullet") # IP Bullet, PTZ, Dome, ANPR Special
    resolution = Column(String(50), default="1080p")     # 720p, 1080p, 4K
    fps = Column(Integer, default=25)
    
    # Interoperability & VMS Federation (Model 3)
    protocol = Column(String(50), default="RTSP")        # RTSP, ONVIF, RTMP, HTTP-FLV, VMS-API
    stream_url = Column(String(500), nullable=True)
    vms_type = Column(String(100), default="Milestone")  # Milestone, Genetec, Qognify, Nx Witness, Standalone NVR
    storage_type = Column(String(100), default="Local NVR") # Local NVR, Cloud S3, Hybrid
    retention_days = Column(Integer, default=15)
    
    # Operational Status
    status = Column(String(50), default="ACTIVE")        # ACTIVE, DEGRADED, INACTIVE, MAINTENANCE
    is_public_domain = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department = relationship("Department", back_populates="cameras")
    health = relationship("CameraHealth", back_populates="camera", uselist=False)
    sightings = relationship("VehicleSighting", back_populates="camera")

class CameraHealth(Base):
    __tablename__ = "camera_health"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    camera_id = Column(String(36), ForeignKey("cameras.id"), unique=True, nullable=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    latency_ms = Column(Integer, default=45)
    packet_loss = Column(Float, default=0.2)
    cpu_usage = Column(Float, default=34.5)
    memory_usage = Column(Float, default=52.0)
    status = Column(String(50), default="ONLINE")        # ONLINE, OFFLINE, DEGRADED

    camera = relationship("Camera", back_populates="health")

class VehicleSighting(Base):
    __tablename__ = "vehicle_sightings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    plate_text = Column(String(50), nullable=False, index=True)
    normalized_plate = Column(String(50), nullable=False, index=True)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    confidence = Column(Float, default=0.92)
    vehicle_type = Column(String(50), default="Car")     # Car, SUV, Motorcycle, Truck, Bus, Auto-Rickshaw
    vehicle_color = Column(String(50), default="White")
    speed_kmh = Column(Float, default=55.0)
    direction = Column(String(50), default="Northbound")
    bbox_json = Column(Text, nullable=True)              # [x, y, w, h]
    evidence_uri = Column(String(500), nullable=True)    # Snapshot image URL
    evidence_hash = Column(String(64), nullable=True)    # SHA-256 integrity hash for Sec 65B
    
    camera = relationship("Camera", back_populates="sightings")
    alerts = relationship("Alert", back_populates="sighting")

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    list_name = Column(String(100), default="Stolen Vehicles Registry")
    entity_type = Column(String(50), default="VEHICLE")  # VEHICLE, PERSON
    vehicle_number = Column(String(50), nullable=False, index=True)
    owner_name = Column(String(255), nullable=True)
    vehicle_make_model = Column(String(255), default="Maruti Suzuki Swift")
    vehicle_color = Column(String(50), default="Red")
    risk_level = Column(String(50), default="HIGH")      # CRITICAL, HIGH, MEDIUM, LOW
    reason = Column(String(500), default="Reported Stolen under IPC 379")
    case_fir_number = Column(String(100), default="FIR-2026/AHM/0981")
    registered_authority = Column(String(100), default="Ahmedabad City Police / eGujCop")
    status = Column(String(50), default="ACTIVE")        # ACTIVE, INACTIVE
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    alerts = relationship("Alert", back_populates="watchlist")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    alert_uid = Column(String(50), unique=True, nullable=False) # e.g. ALT-20260909-001
    watchlist_id = Column(String(36), ForeignKey("watchlists.id"), nullable=True)
    sighting_id = Column(String(36), ForeignKey("vehicle_sightings.id"), nullable=False)
    camera_id = Column(String(36), nullable=False)
    plate_text = Column(String(50), nullable=False)
    risk_level = Column(String(50), default="HIGH")      # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(50), default="NEW")           # NEW, ACKNOWLEDGED, INVESTIGATING, RESOLVED, FALSE_POSITIVE
    remarks = Column(Text, nullable=True)
    dispatched_unit = Column(String(100), nullable=True) # e.g. "PCR Van 07 - Gandhinagar"
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    watchlist = relationship("Watchlist", back_populates="alerts")
    sighting = relationship("VehicleSighting", back_populates="alerts")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), default="system")
    action = Column(String(100), nullable=False)        # SIGHTING_SEARCH, ALERT_ACK, WATCHLIST_EDIT, EVIDENCE_EXPORT
    resource = Column(String(255), nullable=False)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(50), default="127.0.0.1")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    signature_hash = Column(String(64), nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="INVESTIGATOR") # SUPER_ADMIN, STATE_COMMAND, DISTRICT_OFFICER, CONTROL_ROOM_OPERATOR, INVESTIGATOR, DEPARTMENT_ADMIN, AUDITOR
    jurisdiction_district = Column(String(100), nullable=True) # None = Statewide, or "Ahmedabad", "Surat", etc.
    department_code = Column(String(50), default="HOME_POLICE")
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    fir_number = Column(String(100), nullable=True)
    status = Column(String(50), default="INVESTIGATING") # OPEN, INVESTIGATING, SUBMITTED_TO_COURT, CLOSED
    priority = Column(String(50), default="HIGH") # CRITICAL, HIGH, MEDIUM, LOW
    assigned_investigator = Column(String(255), default="Inspector V. Patel")
    jurisdiction_district = Column(String(100), default="Statewide")
    target_vehicle_plate = Column(String(50), nullable=False, index=True)
    created_from_alert_id = Column(String(36), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    timeline_entries = relationship("CaseTimelineEntry", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")

class CaseTimelineEntry(Base):
    __tablename__ = "case_timeline_entries"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    entry_type = Column(String(50), default="NOTE") # NOTE, SIGHTING, EVIDENCE, STATUS_CHANGE
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
