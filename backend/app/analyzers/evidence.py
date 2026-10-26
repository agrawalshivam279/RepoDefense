import uuid
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalyzedFile, CodeSymbol, Dependency, Evidence
from app.models.project import RepositorySnapshot
from app.schemas.evidence import EvidenceCreate, EvidenceType

logger = structlog.get_logger(__name__)

# Known dependency classifications: (Name, Description, EvidenceType)
_DEPENDENCY_RULES: Dict[str, Tuple[str, str, EvidenceType]] = {
    # Web Frameworks
    "fastapi": ("FastAPI Web Framework", "Asynchronous Python web framework for REST API endpoints and OpenAPI schemas.", EvidenceType.FRAMEWORK),
    "starlette": ("Starlette ASGI Framework", "Lightweight ASGI framework/toolkit for high-performance asyncio services.", EvidenceType.FRAMEWORK),
    "django": ("Django Web Framework", "High-level Python web framework with built-in ORM, admin, and routing.", EvidenceType.FRAMEWORK),
    "flask": ("Flask Microframework", "Lightweight WSGI Python web framework.", EvidenceType.FRAMEWORK),
    "next": ("Next.js React Framework", "Full-stack React framework with SSR, SSG, and App Router architecture.", EvidenceType.FRAMEWORK),
    "react": ("React UI Library", "Declarative component-based UI library.", EvidenceType.FRAMEWORK),
    "express": ("Express.js Web Framework", "Minimalist, flexible Node.js web application framework.", EvidenceType.FRAMEWORK),
    "@nestjs/core": ("NestJS Backend Framework", "Progressive TypeScript framework with dependency injection and modular architecture.", EvidenceType.FRAMEWORK),
    "nestjs": ("NestJS Backend Framework", "Progressive TypeScript framework with dependency injection and modular architecture.", EvidenceType.FRAMEWORK),
    "koa": ("Koa.js Web Framework", "Next-generation web framework for Node.js using async functions.", EvidenceType.FRAMEWORK),
    # Databases & ORMs
    "sqlalchemy": ("SQLAlchemy Database ORM", "SQL toolkit and Object Relational Mapper for Python.", EvidenceType.DATABASE),
    "alembic": ("Alembic Database Migrations", "Database schema migration tool for SQLAlchemy.", EvidenceType.DATABASE),
    "pgvector": ("pgvector Vector Extension", "Open-source vector similarity search extension for PostgreSQL.", EvidenceType.DATABASE),
    "prisma": ("Prisma Database ORM", "Next-generation Node.js/TypeScript ORM with type-safe database queries.", EvidenceType.DATABASE),
    "@prisma/client": ("Prisma Database Client", "Auto-generated, type-safe database client for TypeScript/Node.js.", EvidenceType.DATABASE),
    "typeorm": ("TypeORM Database ORM", "TypeScript ORM supporting Active Record and Data Mapper patterns.", EvidenceType.DATABASE),
    "drizzle-orm": ("Drizzle ORM", "TypeScript ORM with compile-time safety and SQL-like syntax.", EvidenceType.DATABASE),
    "mongoose": ("Mongoose ODM", "MongoDB object modeling tool for Node.js asynchronous environments.", EvidenceType.DATABASE),
    "redis": ("Redis In-Memory Data Store", "In-memory database, cache, and message broker.", EvidenceType.DATABASE),
    "ioredis": ("ioredis Client", "Robust, performance-focused Redis client for Node.js.", EvidenceType.DATABASE),
    "asyncpg": ("asyncpg PostgreSQL Driver", "High-performance asynchronous PostgreSQL client library for Python.", EvidenceType.DATABASE),
    "psycopg": ("psycopg PostgreSQL Driver", "PostgreSQL database adapter for Python.", EvidenceType.DATABASE),
    "psycopg2": ("psycopg2 PostgreSQL Driver", "PostgreSQL database adapter for Python.", EvidenceType.DATABASE),
    # Authentication & Security
    "supabase": ("Supabase Client & Auth", "Client SDK for Supabase authentication, database, and storage.", EvidenceType.AUTH),
    "@supabase/supabase-js": ("Supabase JS Client & Auth", "JavaScript/TypeScript SDK for Supabase authentication and database.", EvidenceType.AUTH),
    "next-auth": ("NextAuth.js Authentication", "Complete open-source authentication solution for Next.js applications.", EvidenceType.AUTH),
    "@auth/core": ("Auth.js Core", "Framework-agnostic authentication engine for modern web apps.", EvidenceType.AUTH),
    "jsonwebtoken": ("JSON Web Token (JWT) Library", "Compact, URL-safe means of representing claims between parties.", EvidenceType.AUTH),
    "jose": ("JOSE Encryption & Signing", "Universal Javascript Object Signing and Encryption library for JWT/JWS.", EvidenceType.AUTH),
    "passlib": ("Passlib Password Hashing", "Comprehensive password hashing framework for Python.", EvidenceType.AUTH),
    "bcrypt": ("bcrypt Password Hashing", "Cryptographic password hashing library.", EvidenceType.AUTH),
    # Queues & Background Workers
    "arq": ("ARQ Asyncio Job Queue", "Lightweight, async Redis-based job queue for Python.", EvidenceType.QUEUE),
    "celery": ("Celery Distributed Task Queue", "Asynchronous task queue/job queue based on distributed message passing.", EvidenceType.QUEUE),
    "bullmq": ("BullMQ Message Queue", "Redis-based distributed queue for Node.js and TypeScript.", EvidenceType.QUEUE),
    "bull": ("Bull Message Queue", "Redis-based message queue for Node.js applications.", EvidenceType.QUEUE),
    "rq": ("Redis Queue (RQ)", "Simple Python library for queueing jobs and processing in the background.", EvidenceType.QUEUE),
}

_AUTH_KEYWORDS: Set[str] = {
    "auth", "login", "jwt", "token", "current_user", "session",
    "permission", "protect", "security", "credential",
}


def extract_evidence(
    project_id: uuid.UUID,
    files: Sequence[AnalyzedFile],
    symbols: Sequence[CodeSymbol],
    dependencies: Sequence[Dependency],
    file_map: Optional[Dict[uuid.UUID, AnalyzedFile]] = None,
) -> List[EvidenceCreate]:
    """Deterministically extracts load-bearing architectural evidence from codebase analysis.

    Evaluates dependencies, AST symbols (endpoints, models, auth guards), and infrastructure
    manifests, returning structured EvidenceCreate records.
    """
    evidence_list: List[EvidenceCreate] = []
    seen_keys: Set[Tuple[str, str, str]] = set()

    def _add_evidence(
        ev_type: EvidenceType,
        title: str,
        description: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> None:
        key = (ev_type.value, title, file_path)
        if key not in seen_keys:
            seen_keys.add(key)
            evidence_list.append(
                EvidenceCreate(
                    project_id=project_id,
                    evidence_type=ev_type,
                    title=title,
                    description=description,
                    file_path=file_path,
                    start_line=max(1, start_line),
                    end_line=max(start_line, end_line),
                )
            )

    # 1. Evaluate Dependencies against Rule Book
    for dep in dependencies:
        pkg_lower = dep.name.lower().strip()
        if pkg_lower in _DEPENDENCY_RULES:
            title, desc, ev_type = _DEPENDENCY_RULES[pkg_lower]
            _add_evidence(
                ev_type=ev_type,
                title=title,
                description=f"{desc} Extracted from '{dep.source_file}' (version: {dep.version}).",
                file_path=dep.source_file,
                start_line=1,
                end_line=1,
            )

    # 2. Evaluate AST Symbols
    endpoint_count = 0
    model_count = 0
    auth_count = 0

    fmap = file_map or {f.id: f for f in files}

    for sym in symbols:
        af = fmap.get(sym.file_id)
        if not af:
            continue

        sym_name_lower = sym.name.lower()
        sig_lower = (sym.signature or "").lower()
        doc_lower = (sym.docstring or "").lower()

        # A. API Endpoints
        is_endpoint = (
            sym.symbol_type == "endpoint"
            or any(kw in sig_lower for kw in ["@app.", "@router.", "@api."])
            or any(kw in doc_lower for kw in ["@app.", "@router.", "@api."])
        )
        if is_endpoint and endpoint_count < 25:
            endpoint_count += 1
            _add_evidence(
                ev_type=EvidenceType.API_ENDPOINT,
                title=f"API Route: {sym.name}",
                description=f"Route handler '{sym.name}' defining an HTTP API endpoint in {af.path}.",
                file_path=af.path,
                start_line=sym.start_line,
                end_line=sym.end_line,
            )

        # B. Auth Guards / Middleware / Tokens
        is_auth = (
            any(kw in sym_name_lower for kw in _AUTH_KEYWORDS)
            or any(kw in sig_lower for kw in ["auth", "get_current_user", "verify_token", "jwt"])
        )
        if is_auth and not is_endpoint and auth_count < 10:
            auth_count += 1
            _add_evidence(
                ev_type=EvidenceType.AUTH,
                title=f"Authentication Logic: {sym.name}",
                description=f"Security/auth component '{sym.name}' managing authentication or access control in {af.path}.",
                file_path=af.path,
                start_line=sym.start_line,
                end_line=sym.end_line,
            )

        # C. Data Models & Entities
        is_model = (
            sym.symbol_type == "class"
            and any(kw in sig_lower for kw in ["(base)", "(model)", "(schema)", "tablename", "declarative"])
        )
        if is_model and model_count < 15:
            model_count += 1
            _add_evidence(
                ev_type=EvidenceType.DATABASE,
                title=f"Data Model: {sym.name}",
                description=f"Persistent database model '{sym.name}' declared in {af.path}.",
                file_path=af.path,
                start_line=sym.start_line,
                end_line=sym.end_line,
            )

    # 3. Evaluate Infrastructure Files
    for af in files:
        fname = Path(af.path).name.lower()
        fpath_lower = af.path.lower()

        if fname == "dockerfile" or fname.startswith("dockerfile."):
            _add_evidence(
                ev_type=EvidenceType.INFRASTRUCTURE,
                title=f"Docker Containerization: {Path(af.path).name}",
                description=f"Dockerfile specification defining container build and runtime environment in {af.path}.",
                file_path=af.path,
                start_line=1,
                end_line=max(1, min(50, af.total_lines)),
            )
        elif fname in {"docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"}:
            _add_evidence(
                ev_type=EvidenceType.INFRASTRUCTURE,
                title="Docker Compose Multi-Service Orchestration",
                description=f"Multi-service container configuration defining local or production architecture in {af.path}.",
                file_path=af.path,
                start_line=1,
                end_line=max(1, min(50, af.total_lines)),
            )
        elif ".github/workflows" in fpath_lower and (fname.endswith(".yml") or fname.endswith(".yaml")):
            _add_evidence(
                ev_type=EvidenceType.INFRASTRUCTURE,
                title=f"CI/CD Pipeline: {Path(af.path).name}",
                description=f"GitHub Actions automation workflow for testing, building, or deployment in {af.path}.",
                file_path=af.path,
                start_line=1,
                end_line=max(1, min(50, af.total_lines)),
            )

    return evidence_list


async def extract_and_persist_evidence(
    session: AsyncSession,
    project_id: uuid.UUID,
    snapshot_id: Optional[uuid.UUID] = None,
) -> List[Evidence]:
    """Extracts architectural evidence for a project snapshot and persists records to PostgreSQL.

    Idempotently clears prior evidence for the project before writing new records.
    """
    logger.info("extract_evidence_started", project_id=str(project_id), snapshot_id=str(snapshot_id) if snapshot_id else None)

    # Resolve snapshot if not explicitly provided
    resolved_snapshot_id = snapshot_id
    if not resolved_snapshot_id:
        stmt_snap = (
            select(RepositorySnapshot.id)
            .where(RepositorySnapshot.project_id == project_id)
            .order_by(RepositorySnapshot.created_at.desc())
            .limit(1)
        )
        resolved_snapshot_id = (await session.execute(stmt_snap)).scalar_one_or_none()

    files: List[AnalyzedFile] = []
    symbols: List[CodeSymbol] = []
    file_map: Dict[uuid.UUID, AnalyzedFile] = {}

    if resolved_snapshot_id:
        stmt_files = select(AnalyzedFile).where(AnalyzedFile.snapshot_id == resolved_snapshot_id)
        files = list((await session.execute(stmt_files)).scalars().all())
        file_map = {f.id: f for f in files}

        if files:
            file_ids = [f.id for f in files]
            stmt_syms = select(CodeSymbol).where(CodeSymbol.file_id.in_(file_ids))
            symbols = list((await session.execute(stmt_syms)).scalars().all())

    # Fetch project dependencies
    stmt_deps = select(Dependency).where(Dependency.project_id == project_id)
    dependencies = list((await session.execute(stmt_deps)).scalars().all())

    # Deterministically extract evidence
    evidence_payloads = extract_evidence(
        project_id=project_id,
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        file_map=file_map,
    )

    # Idempotent replacement: delete previous evidence for this project
    del_stmt = delete(Evidence).where(Evidence.project_id == project_id)
    await session.execute(del_stmt)

    # Bulk persist new evidence records
    created_records: List[Evidence] = []
    for item in evidence_payloads:
        ev = Evidence(
            id=uuid.uuid4(),
            project_id=project_id,
            evidence_type=item.evidence_type.value,
            title=item.title,
            description=item.description,
            file_path=item.file_path,
            start_line=item.start_line,
            end_line=item.end_line,
        )
        session.add(ev)
        created_records.append(ev)

    await session.commit()
    logger.info("extract_evidence_completed", project_id=str(project_id), count=len(created_records))
    return created_records
