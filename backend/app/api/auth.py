from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from backend.app.core.database import get_db
from backend.app.core.security import (
    verify_password,
    create_access_token,
    get_current_user,
    require_role
)
from backend.app.models.orm import User

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    full_name: str
    role: str
    jurisdiction_district: Optional[str] = None

class UserProfileOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    jurisdiction_district: Optional[str] = None
    department_code: str
    is_active: bool

@router.post("/login", response_model=TokenResponse)
def login(creds: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate officer credentials and return a signed JWT token."""
    user = db.query(User).filter(User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid police officer credentials or account inactive"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended by State Command"
        )

    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "district": user.jurisdiction_district
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        jurisdiction_district=user.jurisdiction_district
    )

@router.get("/me", response_model=UserProfileOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns profile and RBAC permissions of the authenticated officer."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return UserProfileOut(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        jurisdiction_district=current_user.jurisdiction_district,
        department_code=current_user.department_code,
        is_active=current_user.is_active
    )

@router.get("/users", response_model=List[UserProfileOut])
def list_system_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role("SUPER_ADMIN", "STATE_COMMAND", "AUDITOR"))
):
    """Lists all active officers and roles across Gujarat Police jurisdiction."""
    users = db.query(User).all()
    return [
        UserProfileOut(
            id=u.id,
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            jurisdiction_district=u.jurisdiction_district,
            department_code=u.department_code,
            is_active=u.is_active
        )
        for u in users
    ]

# =====================================================================
# PHASE D: AUDIT TRAIL & HIERARCHICAL ROLES ENDPOINTS
# =====================================================================

from backend.app.models.schema import AuditLogOut, AuditChainVerificationOut, RoleScopeOut
from backend.app.services.audit_service import audit_service
from backend.app.core.security import ROLE_SCOPES, ROLE_DESCRIPTIONS, require_permission

@router.get("/roles", response_model=List[RoleScopeOut])
def get_role_matrix():
    """Returns the 5-tier hierarchical RBAC roles, descriptions, and granular scopes."""
    roles = []
    for r, scopes in ROLE_SCOPES.items():
        if r in ROLE_DESCRIPTIONS:
            roles.append(RoleScopeOut(
                role=r,
                description=ROLE_DESCRIPTIONS[r],
                scopes=scopes
            ))
    return roles

@router.get("/audit/logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = 50,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    db: Session = Depends(get_db),
    auditor: User = Depends(require_permission("audit:read"))
):
    """
    Returns cryptographically signed audit log stream.
    Requires 'audit:read' permission (Auditors, Super Admins, State Commissioners).
    """
    logs = audit_service.get_audit_trail(db, limit=limit, user_id=user_id, action=action, resource=resource)
    return logs

@router.get("/audit/verify-chain", response_model=AuditChainVerificationOut)
def verify_audit_chain_integrity(
    db: Session = Depends(get_db),
    auditor: User = Depends(require_permission("audit:verify"))
):
    """
    Traverses the blockchain-style cryptographic hash chain of all audit events.
    Verifies Section 65B Indian Evidence Act tamper-evidence integrity.
    """
    result = audit_service.verify_chain(db)
    return result

