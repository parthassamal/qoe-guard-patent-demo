"""API routes for QoE-Guard Enterprise."""
from .auth import router as auth_router
from .specs import router as specs_router
from .scenarios import router as scenarios_router
from .validations import router as validations_router
from .governance import router as governance_router

__all__ = [
    "auth_router",
    "specs_router",
    "scenarios_router",
    "validations_router",
    "governance_router",
]
