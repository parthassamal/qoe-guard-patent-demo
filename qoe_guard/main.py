"""
QoE-Guard Enterprise - Main Application Entry Point.

A comprehensive Swagger-to-Scenario validation system with:
- Brittleness scoring
- QoE-aware risk assessment
- Drift classification
- Policy-gated CI integration
- Baseline governance with approvals
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from .db.database import init_db, engine, Base
from .auth.middleware import JWTAuthMiddleware
from .api import (
    auth_router,
    specs_router,
    scenarios_router,
    validations_router,
    governance_router,
)


# Create all tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: nothing to do


# Create FastAPI app
app = FastAPI(
    title="QoE-Guard Enterprise",
    description="""
## Swagger-to-Scenario Validation with Brittleness Scoring and QoE-Aware CI Gating

QoE-Guard is a comprehensive API validation system that:

- **Discovers** OpenAPI specs from Swagger UI pages
- **Extracts** operations into an inventory with multi-select
- **Generates** executable cURL commands
- **Validates** runtime responses against schemas
- **Scores** brittleness and QoE impact risk
- **Classifies** spec vs runtime drift
- **Gates** CI/CD with configurable policies
- **Governs** baseline promotions with approvals

### Key Concepts

- **Brittleness Score (0-100)**: Measures API fragility based on contract complexity, change sensitivity, runtime fragility, and blast radius.
- **QoE Risk Score (0.0-1.0)**: Measures potential impact on Quality of Experience based on changes to critical paths.
- **Drift Classification**: Categorizes changes as spec drift, runtime drift, or undocumented (dangerous) drift.
- **Policy Engine**: Applies configurable rules to determine PASS/WARN/FAIL decisions.
""",
    version="1.0.0",
    openapi_tags=[
        {"name": "Authentication", "description": "User authentication and management"},
        {"name": "Specifications", "description": "OpenAPI spec discovery and management"},
        {"name": "Scenarios", "description": "Test scenario management"},
        {"name": "Validations", "description": "Validation job execution and results"},
        {"name": "Governance", "description": "Baseline promotion and policy management"},
    ],
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add JWT auth middleware
app.add_middleware(JWTAuthMiddleware)

# Include API routers
app.include_router(auth_router)
app.include_router(specs_router)
app.include_router(scenarios_router)
app.include_router(validations_router)
app.include_router(governance_router)

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


# Health check
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Root redirect
@app.get("/", include_in_schema=False)
def root():
    """Redirect to dashboard."""
    return RedirectResponse(url="/dashboard")


# Dashboard
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    """Enterprise dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


# Inventory page
@app.get("/inventory", response_class=HTMLResponse, include_in_schema=False)
async def inventory_page(request: Request):
    """Endpoint inventory page."""
    return templates.TemplateResponse("inventory.html", {"request": request})


# Validation page
@app.get("/validate", response_class=HTMLResponse, include_in_schema=False)
async def validation_page(request: Request):
    """Validation job page."""
    return templates.TemplateResponse("validation.html", {"request": request})


# Governance page
@app.get("/governance", response_class=HTMLResponse, include_in_schema=False)
async def governance_page(request: Request):
    """Baseline governance page."""
    return templates.TemplateResponse("governance.html", {"request": request})


# Settings page
@app.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(request: Request):
    """Settings and configuration page."""
    return templates.TemplateResponse("settings.html", {"request": request})


# Login page
@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("auth.html", {"request": request, "mode": "login"})


# Register page
@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    """Register page."""
    return templates.TemplateResponse("auth.html", {"request": request, "mode": "register"})


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8010"))
    uvicorn.run(app, host="0.0.0.0", port=port)
