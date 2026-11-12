from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.analytics import router as analytics_router
from app.api.v1.arch_defense import router as arch_defense_router
from app.api.v1.architecture import router as architecture_router
from app.api.v1.auth import router as auth_router
from app.api.v1.claims import (
    project_claims_router,
)
from app.api.v1.claims import (
    router as claims_router,
)
from app.api.v1.commit_defense import router as commit_defense_router
from app.api.v1.defense import router as defense_router
from app.api.v1.diagram import router as diagram_router
from app.api.v1.incident_simulation import router as incident_simulation_router
from app.api.v1.pr_defense import router as pr_defense_router
from app.api.v1.projects import router as projects_router
from app.api.v1.pull_requests import router as pr_router
from app.api.v1.questions import router as questions_router
from app.api.v1.stress_test import router as stress_test_router
from app.api.v1.tech_audit import router as tech_audit_router
from app.core.config import settings
from app.core.redis import close_arq_redis_pool
from app.schemas.health import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to handle startup and cleanup events."""
    yield
    await close_arq_redis_pool()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(projects_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(project_claims_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(questions_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(defense_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(claims_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(architecture_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(diagram_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(tech_audit_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(pr_router, prefix=f"{settings.API_V1_STR}/v1")
app.include_router(pr_defense_router, prefix=f"{settings.API_V1_STR}/v1/pr-defense")
app.include_router(commit_defense_router, prefix=f"{settings.API_V1_STR}/v1/commit-defense")
app.include_router(
    incident_simulation_router, prefix=f"{settings.API_V1_STR}/v1/incident-simulation"
)
app.include_router(stress_test_router, prefix=f"{settings.API_V1_STR}/v1/stress-test")
app.include_router(arch_defense_router, prefix=f"{settings.API_V1_STR}/v1/arch-defense")
app.include_router(analytics_router, prefix=f"{settings.API_V1_STR}/v1/analytics")


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Root endpoint returning service identity."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Returns application health and operational status."""
    return HealthResponse(
        status="ok",
        app=settings.PROJECT_NAME,
        version=settings.VERSION,
    )
