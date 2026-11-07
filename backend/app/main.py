from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.architecture import router as architecture_router
from app.api.v1.auth import router as auth_router
from app.api.v1.claims import (
    project_claims_router,
)
from app.api.v1.claims import (
    router as claims_router,
)
from app.api.v1.defense import router as defense_router
from app.api.v1.diagram import router as diagram_router
from app.api.v1.projects import router as projects_router
from app.api.v1.questions import router as questions_router
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
    description=(
        "RepoDefense: AI-driven repository stress testing and "
        "architectural interview simulation platform."
    ),
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
