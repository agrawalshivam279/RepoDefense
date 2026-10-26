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
    "fastapi": ("FastAPI Framework", "Python async REST API framework.", EvidenceType.FRAMEWORK),
    "starlette": ("Starlette Toolkit", "Async ASGI toolkit.", EvidenceType.FRAMEWORK),
    "django": ("Django Framework", "Python web framework with ORM.", EvidenceType.FRAMEWORK),
    "flask": ("Flask Microframework", "WSGI Python web framework.", EvidenceType.FRAMEWORK),
    "next": ("Next.js Framework", "React framework with SSR/App Router.", EvidenceType.FRAMEWORK),
    "react": ("React UI Library", "Component-based UI library.", EvidenceType.FRAMEWORK),
    "express": ("Express.js Framework", "Node.js web framework.", EvidenceType.FRAMEWORK),
    "@nestjs/core": ("NestJS Framework", "TypeScript backend framework.", EvidenceType.FRAMEWORK),
    "nestjs": ("NestJS Framework", "TypeScript backend framework.", EvidenceType.FRAMEWORK),
    "koa": ("Koa.js Framework", "Next-gen Node.js web framework.", EvidenceType.FRAMEWORK),
    # Databases & ORMs
    "sqlalchemy": ("SQLAlchemy ORM", "Python SQL toolkit and ORM.", EvidenceType.DATABASE),
    "alembic": ("Alembic Migrations", "Schema migration tool.", EvidenceType.DATABASE),
    "pgvector": ("pgvector Extension", "Postgres vector search extension.", EvidenceType.DATABASE),
    "prisma": ("Prisma ORM", "Type-safe TypeScript ORM.", EvidenceType.DATABASE),
    "@prisma/client": ("Prisma Client", "TypeScript database client.", EvidenceType.DATABASE),
    "typeorm": ("TypeORM ORM", "TypeScript ORM with Data Mapper.", EvidenceType.DATABASE),
    "drizzle-orm": ("Drizzle ORM", "TypeScript SQL-like ORM.", EvidenceType.DATABASE),
    "mongoose": ("Mongoose ODM", "MongoDB object modeling tool.", EvidenceType.DATABASE),
    "redis": ("Redis Store", "In-memory database, cache, and broker.", EvidenceType.DATABASE),
    "ioredis": ("ioredis Client", "Performance-focused Redis client.", EvidenceType.DATABASE),
    "asyncpg": ("asyncpg Driver", "Async PostgreSQL client for Python.", EvidenceType.DATABASE),
    "psycopg": ("psycopg Driver", "PostgreSQL database adapter.", EvidenceType.DATABASE),
    "psycopg2": ("psycopg2 Driver", "PostgreSQL database adapter.", EvidenceType.DATABASE),
    # Authentication & Security
    "supabase": ("Supabase SDK", "SDK for Supabase auth and DB.", EvidenceType.AUTH),
    "@supabase/supabase-js": ("Supabase JS", "JS client for Supabase auth.", EvidenceType.AUTH),
    "next-auth": ("NextAuth.js", "Authentication for Next.js.", EvidenceType.AUTH),
    "@auth/core": ("Auth.js Core", "Framework-agnostic auth engine.", EvidenceType.AUTH),
    "jsonwebtoken": ("JSON Web Token", "JWT signing & verification.", EvidenceType.AUTH),
    "jose": ("JOSE Framework", "Javascript Object Signing & Encryption.", EvidenceType.AUTH),
    "passlib": ("Passlib Hashing", "Password hashing framework.", EvidenceType.AUTH),
    "bcrypt": ("bcrypt Hashing", "Password hashing library.", EvidenceType.AUTH),
    # Queues & Background Workers
    "arq": ("ARQ Job Queue", "Async Redis-based job queue.", EvidenceType.QUEUE),
    "celery": ("Celery Task Queue", "Distributed task queue.", EvidenceType.QUEUE),
    "bullmq": ("BullMQ Queue", "Redis-based queue for Node.js.", EvidenceType.QUEUE),
    "bull": ("Bull Queue", "Redis-based queue for Node.js.", EvidenceType.QUEUE),
    "rq": ("Redis Queue (RQ)", "Python queue for background jobs.", EvidenceType.QUEUE),
}

_AUTH_KEYWORDS: Set[str] = {
    "auth",
    "login",
    "jwt",
    "token",
    "current_user",
    "session",
    "permission",
    "protect",
    "security",
    "credential",
}


def extract_evidence(
    project_id: uuid.UUID,
    files: Sequence[AnalyzedFile],
    symbols: Sequence[CodeSymbol],
    dependencies: Sequence[Dependency],
    file_map: Optional[Dict[uuid.UUID, AnalyzedFile]] = None,
) -> List[EvidenceCreate]:
    """Deterministically extracts architectural evidence from codebase analysis."""
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

    # 1. Dependencies
    for dep in dependencies:
        pkg_lower = dep.name.lower().strip()
        if pkg_lower in _DEPENDENCY_RULES:
            title, desc, ev_type = _DEPENDENCY_RULES[pkg_lower]
            _add_evidence(
                ev_type=ev_type,
                title=title,
                description=f"{desc} From '{dep.source_file}' ({dep.version}).",
                file_path=dep.source_file,
                start_line=1,
                end_line=1,
            )

    # 2. AST Symbols
    endpoint_count, model_count, auth_count = 0, 0, 0
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
                description=f"Route handler '{sym.name}' defining an API endpoint in {af.path}.",
                file_path=af.path,
                start_line=sym.start_line,
                end_line=sym.end_line,
            )

        # B. Auth Guards
        is_auth = (
            any(kw in sym_name_lower for kw in _AUTH_KEYWORDS)
            or any(kw in sig_lower for kw in ["auth", "get_current_user", "verify_token", "jwt"])
        )
        if is_auth and not is_endpoint and auth_count < 10:
            auth_count += 1
            _add_evidence(
                ev_type=EvidenceType.AUTH,
                title=f"Authentication Logic: {sym.name}",
                description=f"Security component '{sym.name}' managing auth in {af.path}.",
                file_path=af.path,
                start_line=sym.start_line,
                end_line=sym.end_line,
            )

        # C. Data Models
        is_model = sym.symbol_type == "class" and any(
            kw in sig_lower for kw in ["(base)", "(model)", "(schema)", "tablename", "declarative"]
        )
        if is_model and model_count < 15:
            model_count += 1
            _add_evidence(
                ev_type=EvidenceType.DATABASE,
                title=f"Data Model: {sym.name}",
                description=f"Database model '{sym.name}' declared in {af.path}.",
                file_path=af.path,
                start_line=sym.start_line,
                end_line=sym.end_line,
            )

    # 3. Infrastructure Files
    for af in files:
        fname = Path(af.path).name.lower()
        fpath_lower = af.path.lower()

        if fname == "dockerfile" or fname.startswith("dockerfile."):
            _add_evidence(
                ev_type=EvidenceType.INFRASTRUCTURE,
                title=f"Docker Containerization: {Path(af.path).name}",
                description=f"Dockerfile specification defining container build in {af.path}.",
                file_path=af.path,
                start_line=1,
                end_line=max(1, min(50, af.total_lines)),
            )
        elif fname in {"docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"}:
            _add_evidence(
                ev_type=EvidenceType.INFRASTRUCTURE,
                title="Docker Compose Multi-Service Orchestration",
                description=f"Multi-service container configuration in {af.path}.",
                file_path=af.path,
                start_line=1,
                end_line=max(1, min(50, af.total_lines)),
            )
        elif ".github/workflows" in fpath_lower and fname.endswith((".yml", ".yaml")):
            _add_evidence(
                ev_type=EvidenceType.INFRASTRUCTURE,
                title=f"CI/CD Pipeline: {Path(af.path).name}",
                description=f"GitHub Actions automation workflow in {af.path}.",
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
    """Extracts architectural evidence for a project snapshot and persists to PostgreSQL."""
    logger.info(
        "extract_evidence_started",
        project_id=str(project_id),
        snapshot_id=str(snapshot_id) if snapshot_id else None,
    )

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

    stmt_deps = select(Dependency).where(Dependency.project_id == project_id)
    dependencies = list((await session.execute(stmt_deps)).scalars().all())

    evidence_payloads = extract_evidence(
        project_id=project_id,
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        file_map=file_map,
    )

    del_stmt = delete(Evidence).where(Evidence.project_id == project_id)
    await session.execute(del_stmt)

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
    logger.info(
        "extract_evidence_completed",
        project_id=str(project_id),
        count=len(created_records),
    )
    return created_records
