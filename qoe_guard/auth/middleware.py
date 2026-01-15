"""
Authentication middleware and decorators for QoE-Guard Enterprise.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable, List, Optional

from fastapi import Request, HTTPException, status, Depends
from starlette.middleware.base import BaseHTTPMiddleware

from ..db.models import User, Role
from .service import AuthService, get_current_active_user


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication.
    
    Adds user info to request state if valid token is provided.
    Does not block requests without tokens (use require_auth for that).
    """
    
    # Paths that skip authentication entirely
    SKIP_PATHS = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/auth/login",
        "/auth/register",
    }
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for certain paths
        if request.url.path in self.SKIP_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)
        
        # Try to extract and validate token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = AuthService.decode_token(token)
                request.state.user_id = payload.get("sub")
                request.state.user_email = payload.get("email")
                request.state.user_role = payload.get("role")
            except HTTPException:
                # Invalid token - continue without user info
                request.state.user_id = None
                request.state.user_email = None
                request.state.user_role = None
        else:
            request.state.user_id = None
            request.state.user_email = None
            request.state.user_role = None
        
        return await call_next(request)


def require_role(allowed_roles: List[Role]):
    """
    Decorator/dependency to require specific roles.
    
    Usage:
        @router.get("/admin")
        async def admin_route(user: User = Depends(require_role([Role.ADMIN]))):
            ...
    """
    async def role_checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return user
    
    return role_checker


def require_admin():
    """Shortcut for requiring admin role."""
    return require_role([Role.ADMIN])


def require_approver():
    """Shortcut for requiring approver or admin role."""
    return require_role([Role.ADMIN, Role.APPROVER])


def require_developer():
    """Shortcut for requiring developer, approver, or admin role."""
    return require_role([Role.ADMIN, Role.APPROVER, Role.DEVELOPER])


def optional_auth(func: Callable) -> Callable:
    """
    Decorator for routes that can work with or without authentication.
    
    If authenticated, user is passed. If not, user is None.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper
