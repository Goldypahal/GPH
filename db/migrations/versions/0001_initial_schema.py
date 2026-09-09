"""Initial PostGIS 16 Statewide Schema Migration

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS Extension if PostgreSQL dialect
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    # 2. Administrative Boundaries & Districts
    op.create_table(
        'districts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('code', sa.String(length=20), nullable=False, unique=True),
        sa.Column('state', sa.String(length=100), server_default="Gujarat"),
        sa.Column('center_lat', sa.Float(), nullable=False),
        sa.Column('center_lng', sa.Float(), nullable=False),
        sa.Column('boundary_geojson', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'departments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('category', sa.String(length=100), server_default="State Government"),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 3. RBAC & Identity
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        'permissions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=100), nullable=False, unique=True),
        sa.Column('resource', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
    )

    op.create_table(
        'role_permissions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('role_id', sa.String(length=36), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('permission_id', sa.String(length=36), sa.ForeignKey('permissions.id'), nullable=False),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('username', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), server_default="INVESTIGATOR"),
        sa.Column('jurisdiction_district', sa.String(length=100), nullable=True),
        sa.Column('department_code', sa.String(length=50), server_default="HOME_POLICE"),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'user_roles',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role_id', sa.String(length=36), sa.ForeignKey('roles.id'), nullable=False),
    )

    # 4. Cameras & Hardware State
    op.create_table(
        'cameras',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('department_id', sa.String(length=36), sa.ForeignKey('departments.id'), nullable=False),
        sa.Column('logical_camera_id', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False, index=True),
        sa.Column('location_name', sa.String(length=255), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('altitude', sa.Float(), server_default="15.0"),
        sa.Column('fov_angle', sa.Float(), server_default="90.0"),
        sa.Column('fov_range_m', sa.Float(), server_default="80.0"),
        sa.Column('vendor', sa.String(length=100), server_default="Hikvision"),
        sa.Column('model', sa.String(length=100), server_default="DS-2CD2043G2-I"),
        sa.Column('camera_type', sa.String(length=50), server_default="IP Bullet"),
        sa.Column('resolution', sa.String(length=50), server_default="1080p"),
        sa.Column('fps', sa.Integer(), server_default="25"),
        sa.Column('protocol', sa.String(length=50), server_default="RTSP"),
        sa.Column('stream_url', sa.String(length=500), nullable=True),
        sa.Column('vms_type', sa.String(length=100), server_default="Milestone"),
        sa.Column('storage_type', sa.String(length=100), server_default="Local NVR"),
        sa.Column('retention_days', sa.Integer(), server_default="15"),
        sa.Column('status', sa.String(length=50), server_default="ACTIVE", index=True),
        sa.Column('is_public_domain', sa.Boolean(), server_default=sa.true()),
        sa.Column('share_scope', sa.String(length=50), server_default="STATEWIDE_FEDERATED"),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'camera_credentials',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), unique=True, nullable=False),
        sa.Column('username', sa.String(length=100), server_default="admin"),
        sa.Column('encrypted_password', sa.String(length=255), nullable=True),
        sa.Column('auth_type', sa.String(length=50), server_default="BASIC"),
        sa.Column('port', sa.Integer(), server_default="554"),
    )

    op.create_table(
        'camera_configurations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), unique=True, nullable=False),
        sa.Column('config_json', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'camera_health',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), unique=True, nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), server_default="45"),
        sa.Column('packet_loss', sa.Float(), server_default="0.2"),
        sa.Column('cpu_usage', sa.Float(), server_default="34.5"),
        sa.Column('memory_usage', sa.Float(), server_default="52.0"),
        sa.Column('clock_drift_ms', sa.Float(), server_default="5.0"),
        sa.Column('status', sa.String(length=50), server_default="ONLINE"),
    )

    op.create_table(
        'federation_access_requests',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('request_uid', sa.String(length=50), unique=True, nullable=False, index=True),
        sa.Column('requester_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('requester_department_code', sa.String(length=50), nullable=False),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('target_department_code', sa.String(length=50), nullable=False),
        sa.Column('legal_justification', sa.Text(), nullable=False),
        sa.Column('fir_number', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), server_default="PENDING"),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 5. AI Vision, Sightings, and Embeddings
    op.create_table(
        'ai_models',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('framework', sa.String(length=50), server_default="PyTorch"),
        sa.Column('weights_uri', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'ai_model_deployments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('model_id', sa.String(length=36), sa.ForeignKey('ai_models.id'), nullable=False),
        sa.Column('node_identifier', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default="RUNNING"),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'vehicle_tracks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('first_seen', sa.DateTime(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('best_plate', sa.String(length=50), nullable=True),
        sa.Column('best_confidence', sa.Float(), server_default="0.0"),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        'plate_detections',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('plate_text', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), server_default="0.90"),
        sa.Column('crop_uri', sa.String(length=500), nullable=True),
        sa.Column('bbox_json', sa.Text(), nullable=True),
    )

    op.create_table(
        'anpr_results',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('plate_detection_id', sa.String(length=36), sa.ForeignKey('plate_detections.id'), nullable=False),
        sa.Column('raw_ocr_text', sa.String(length=50), nullable=False),
        sa.Column('normalized_plate', sa.String(length=50), nullable=False, index=True),
        sa.Column('ocr_confidence', sa.Float(), server_default="0.90"),
        sa.Column('optical_corrected', sa.Boolean(), server_default=sa.false()),
        sa.Column('ocr_engine', sa.String(length=50), server_default="PaddleOCR"),
    )

    op.create_table(
        'vehicle_sightings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('plate_text', sa.String(length=50), nullable=False, index=True),
        sa.Column('normalized_plate', sa.String(length=50), nullable=False, index=True),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('confidence', sa.Float(), server_default="0.92"),
        sa.Column('vehicle_type', sa.String(length=50), server_default="Car"),
        sa.Column('vehicle_color', sa.String(length=50), server_default="White"),
        sa.Column('speed_kmh', sa.Float(), server_default="55.0"),
        sa.Column('direction', sa.String(length=50), server_default="Northbound"),
        sa.Column('bbox_json', sa.Text(), nullable=True),
        sa.Column('evidence_uri', sa.String(length=500), nullable=True),
        sa.Column('evidence_hash', sa.String(length=64), nullable=True),
    )

    op.create_table(
        'vehicle_embeddings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('sighting_id', sa.String(length=36), sa.ForeignKey('vehicle_sightings.id'), nullable=False),
        sa.Column('vehicle_crop_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding_json', sa.Text(), nullable=True),
        sa.Column('model_name', sa.String(length=100), server_default="osnet_x1_0"),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 6. Watchlists & Alerts
    op.create_table(
        'watchlists',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('list_name', sa.String(length=100), server_default="Stolen Vehicles Registry"),
        sa.Column('entity_type', sa.String(length=50), server_default="VEHICLE"),
        sa.Column('vehicle_number', sa.String(length=50), nullable=False, index=True),
        sa.Column('owner_name', sa.String(length=255), nullable=True),
        sa.Column('vehicle_make_model', sa.String(length=100), nullable=True),
        sa.Column('vehicle_color', sa.String(length=50), nullable=True),
        sa.Column('risk_level', sa.String(length=50), server_default="HIGH"),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('case_fir_number', sa.String(length=100), nullable=True),
        sa.Column('registered_authority', sa.String(length=255), server_default="Gujarat Police"),
        sa.Column('status', sa.String(length=50), server_default="ACTIVE"),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'watchlist_entries',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('watchlist_id', sa.String(length=36), sa.ForeignKey('watchlists.id'), nullable=False),
        sa.Column('identifier', sa.String(length=100), nullable=False, index=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('risk_level', sa.String(length=50), server_default="HIGH"),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'alerts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('alert_uid', sa.String(length=50), unique=True, nullable=False, index=True),
        sa.Column('watchlist_id', sa.String(length=36), sa.ForeignKey('watchlists.id'), nullable=True),
        sa.Column('sighting_id', sa.String(length=36), sa.ForeignKey('vehicle_sightings.id'), nullable=False),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('plate_text', sa.String(length=50), nullable=False),
        sa.Column('risk_level', sa.String(length=50), server_default="HIGH"),
        sa.Column('status', sa.String(length=50), server_default="NEW"),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('dispatched_unit', sa.String(length=100), nullable=True),
    )

    op.create_table(
        'alert_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('alert_id', sa.String(length=36), sa.ForeignKey('alerts.id'), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('actor', sa.String(length=100), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 7. Cases, Dossiers & Chain of Custody
    op.create_table(
        'cases',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_number', sa.String(length=50), unique=True, nullable=False, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('fir_number', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), server_default="INVESTIGATING"),
        sa.Column('priority', sa.String(length=50), server_default="HIGH"),
        sa.Column('assigned_investigator', sa.String(length=255), server_default="Inspector V. Patel"),
        sa.Column('jurisdiction_district', sa.String(length=100), server_default="Statewide"),
        sa.Column('target_vehicle_plate', sa.String(length=50), nullable=False, index=True),
        sa.Column('created_from_alert_id', sa.String(length=36), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'case_assignments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('assigned_role', sa.String(length=50), server_default="PRIMARY_INVESTIGATOR"),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'case_notes',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('author_id', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'case_timeline_entries',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('entry_type', sa.String(length=50), server_default="NOTE"),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(length=255), server_default="Inspector V. Patel"),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'case_evidence',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('sighting_id', sa.String(length=36), sa.ForeignKey('vehicle_sightings.id'), nullable=False),
        sa.Column('evidence_hash', sa.String(length=64), nullable=True),
        sa.Column('sec_65b_cert_ref', sa.String(length=100), nullable=True),
        sa.Column('attached_at', sa.DateTime(), nullable=True),
    )

    # 8. Evidence Vault & Section 65B
    op.create_table(
        'evidence',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('sighting_id', sa.String(length=36), sa.ForeignKey('vehicle_sightings.id'), nullable=True),
        sa.Column('camera_id', sa.String(length=36), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('frame_hash', sa.String(length=64), nullable=False),
        sa.Column('plate_crop_hash', sa.String(length=64), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), server_default="0.95"),
        sa.Column('model_version', sa.String(length=50), server_default="GIVIN-Vision-1.2"),
        sa.Column('object_uri', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'evidence_access_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('evidence_id', sa.String(length=36), sa.ForeignKey('evidence.id'), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('access_type', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('justification', sa.String(length=255), nullable=True),
        sa.Column('accessed_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'evidence_exports',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('evidence_ids_json', sa.Text(), nullable=False),
        sa.Column('exported_by', sa.String(length=100), nullable=False),
        sa.Column('export_hash', sa.String(length=64), nullable=False),
        sa.Column('destination', sa.String(length=255), server_default="STATE_COURT_PORTAL"),
        sa.Column('exported_at', sa.DateTime(), nullable=True),
    )

    # 9. Cryptographic Audit Chain
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('prev_signature_hash', sa.String(length=64), nullable=True),
        sa.Column('signature_hash', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('prev_hash', sa.String(length=64), nullable=True),
        sa.Column('event_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 10. Government Integrations & Telemetry
    op.create_table(
        'integrations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider_code', sa.String(length=50), unique=True, nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), server_default="ONLINE"),
        sa.Column('is_enabled', sa.Boolean(), server_default=sa.true()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'integration_credentials',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('integration_id', sa.String(length=36), sa.ForeignKey('integrations.id'), nullable=False),
        sa.Column('auth_type', sa.String(length=50), server_default="OAUTH2"),
        sa.Column('credential_encrypted', sa.Text(), nullable=True),
    )

    op.create_table(
        'system_health_nodes',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('node_id', sa.String(length=100), unique=True, nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default="HEALTHY"),
        sa.Column('metrics_json', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    tables = [
        'system_health_nodes', 'integration_credentials', 'integrations',
        'audit_events', 'audit_logs', 'evidence_exports', 'evidence_access_logs', 'evidence',
        'case_evidence', 'case_timeline_entries', 'case_notes', 'case_assignments', 'cases',
        'alert_events', 'alerts', 'watchlist_entries', 'watchlists',
        'vehicle_embeddings', 'vehicle_sightings', 'anpr_results', 'plate_detections',
        'vehicle_tracks', 'ai_model_deployments', 'ai_models',
        'federation_access_requests', 'camera_health', 'camera_configurations', 'camera_credentials',
        'cameras', 'user_roles', 'users', 'role_permissions', 'permissions', 'roles',
        'departments', 'districts'
    ]
    for tbl in tables:
        op.drop_table(tbl)
