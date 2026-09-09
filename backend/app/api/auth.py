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
