"""
GIVIN Inter-Departmental Camera Federation Service.
Governs multi-tenant data segregation across Gujarat's 26 government departments,
enforces share_scope policies, and manages cross-department feed sharing requests.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.orm import Camera, Department, User, FederationAccessRequest
from backend.app.services.audit_service import audit_service
from backend.app.services.event_bus import event_bus, EventBus

class DepartmentFederationService:
    """
    Manages inter-department camera federation and feed sharing permissions.
    """

    STATEWIDE_ROLES = {"SUPER_ADMIN", "DGP_STATE_COMMISSIONER", "STATE_COMMAND"}

    @classmethod
    def can_user_access_camera(
        cls,
        db: Session,
        user: User,
        camera: Camera
    ) -> Tuple[bool, str]:
        """
        Determines if user is authorized to view or stream specified camera feed:
        1. Statewide Command (Super Admin / DGP) -> Universal Access.
        2. Own Department Camera -> Universal Access.
        3. Camera share_scope == 'STATEWIDE_FEDERATED' -> Access Granted.
        4. Camera share_scope == 'DISTRICT_WIDE' & User district matches -> Access Granted.
        5. Active Approved Federation Request exists -> Access Granted.
        6. Otherwise -> Denied (Filing Federation Request required).
        """
        if not user:
            return False, "Unauthenticated access denied."

        # 1. Statewide Command override
        if user.role in cls.STATEWIDE_ROLES:
            return True, "Authorized via Statewide Command jurisdiction override."

        # Fetch camera department
        dept = camera.department or db.query(Department).filter(Department.id == camera.department_id).first()
        dept_code = dept.code if dept else "UNKNOWN"

        # 2. Same Department
        if user.department_code and user.department_code == dept_code:
            return True, f"Authorized via primary department membership ({dept_code})."

        # 3. Camera is federated statewide
        scope = getattr(camera, "share_scope", "STATEWIDE_FEDERATED")
        if scope == "STATEWIDE_FEDERATED":
            return True, f"Authorized: camera is public-domain federated across all 26 departments."

        # 4. District-wide scope
        if scope == "DISTRICT_WIDE":
            if user.jurisdiction_district and camera.district and \
               user.jurisdiction_district.lower() == camera.district.lower():
                return True, f"Authorized: camera shared district-wide in {camera.district}."

        # 5. Check active approved federation request
        now = datetime.now(timezone.utc)
        active_req = (
            db.query(FederationAccessRequest)
            .filter(
                FederationAccessRequest.camera_id == camera.id,
                FederationAccessRequest.requester_user_id == user.id,
                FederationAccessRequest.status == "APPROVED",
                FederationAccessRequest.valid_until > now
            )
            .first()
        )
        if active_req:
            remaining_mins = round((active_req.valid_until.replace(tzinfo=timezone.utc) - now).total_seconds() / 60.0, 0)
            return True, f"Authorized via approved federation permit {active_req.request_uid} ({remaining_mins} mins remaining)."

        # Denied
        return False, (
            f"Access Restricted: Camera belongs to Department '{dept_code}' with scope '{scope}'. "
            f"Cross-department access requires submitting a formal Federation Access Request."
        )

    @classmethod
    def create_access_request(
        cls,
        db: Session,
        user: User,
        camera_id: str,
        legal_justification: str,
        fir_number: Optional[str] = None,
        duration_hours: int = 24
    ) -> FederationAccessRequest:
        """Submits an inter-departmental feed access request with legal FIR justification."""
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise ValueError(f"Camera '{camera_id}' not found.")

        dept = camera.department or db.query(Department).filter(Department.id == camera.department_id).first()
        target_dept = dept.code if dept else "OTHER"

        req_uid = f"FED-REQ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        req = FederationAccessRequest(
            request_uid=req_uid,
            requester_user_id=user.id,
            requester_department_code=user.department_code or "HOME_POLICE",
            camera_id=camera.id,
            target_department_code=target_dept,
            legal_justification=legal_justification,
            fir_number=fir_number,
            status="PENDING"
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        # Audit log creation
        audit_service.log_action(
            db=db,
            user_id=user.username,
            action="FEDERATION_REQUEST_SUBMITTED",
            resource=f"CAMERA:{camera.logical_camera_id}",
            details_json=f"Request {req_uid} filed for {target_dept} camera. FIR: {fir_number}"
        )

        return req

    @classmethod
    def approve_access_request(
        cls,
        db: Session,
        request_id: str,
        approver_user: User,
        status: str = "APPROVED",
        duration_hours: int = 24,
        remarks: Optional[str] = None
    ) -> FederationAccessRequest:
        """Approves or rejects a federation access request."""
        req = db.query(FederationAccessRequest).filter(FederationAccessRequest.id == request_id).first()
        if not req:
            req = db.query(FederationAccessRequest).filter(FederationAccessRequest.request_uid == request_id).first()
        if not req:
            raise ValueError(f"Federation request '{request_id}' not found.")

        now = datetime.now(timezone.utc)
        req.status = status
        req.approved_by = approver_user.username
        if status == "APPROVED":
            req.valid_until = now + timedelta(hours=duration_hours)

        db.commit()
        db.refresh(req)

        # Audit log resolution
        audit_service.log_action(
            db=db,
            user_id=approver_user.username,
            action=f"FEDERATION_REQUEST_{status}",
            resource=f"REQUEST:{req.request_uid}",
            details_json=f"Request {status} by {approver_user.username}. Valid for {duration_hours}h. Remarks: {remarks}"
        )

        return req

    @classmethod
    def list_requests(
        cls,
        db: Session,
        status: Optional[str] = None,
        requester_id: Optional[str] = None
    ) -> List[FederationAccessRequest]:
        """Lists pending and active federation access requests."""
        query = db.query(FederationAccessRequest)
        if status:
            query = query.filter(FederationAccessRequest.status == status)
        if requester_id:
            query = query.filter(FederationAccessRequest.requester_user_id == requester_id)
        return query.order_by(FederationAccessRequest.created_at.desc()).all()

federation_service = DepartmentFederationService()
