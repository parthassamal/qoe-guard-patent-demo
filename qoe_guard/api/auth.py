"""
Authentication API routes.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..db.models import User, Role
from ..auth.service import (
    AuthService,
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    get_current_active_user,
)
from ..auth.middleware import require_role

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RoleUpdate(BaseModel):
    """Request to update user role."""
    role: str


class UserListResponse(BaseModel):
    """List of users response."""
    users: List[UserResponse]
    total: int


@router.post("/register", response_model=TokenResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.
    
    Default role is DEVELOPER. First user gets ADMIN role.
    """
    # Check if this is the first user (make them admin)
    user_count = db.query(User).count()
    role = Role.ADMIN if user_count == 0 else Role.DEVELOPER
    
    user = AuthService.register_user(db, user_data, role=role)
    access_token = AuthService.create_access_token(user)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=1440 * 60,  # 24 hours in seconds
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Login with email and password.
    
    Returns JWT access token on success.
    """
    return AuthService.login(db, credentials)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current authenticated user info.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.get("/users", response_model=UserListResponse)
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN])),
):
    """
    List all users (admin only).
    """
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    
    return UserListResponse(
        users=[
            UserResponse(
                id=u.id,
                email=u.email,
                name=u.name,
                role=u.role.value,
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ],
        total=total,
    )


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: str,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN])),
):
    """
    Update a user's role (admin only).
    """
    try:
        new_role = Role(role_update.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role_update.role}. Valid roles: {[r.value for r in Role]}",
        )
    
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    
    user = AuthService.update_user_role(db, user_id, new_role)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.put("/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN])),
):
    """
    Deactivate a user account (admin only).
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_active = False
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
    )
