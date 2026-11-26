import uuid
from typing import Any

import anyio
import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.project import Project, User
from app.schemas.auth import TokenPayload

logger = structlog.get_logger(__name__)

security_scheme = HTTPBearer(
    auto_error=True,
    description="Supabase JWT Bearer Token",
)

_ASYMMETRIC_ALGS = frozenset({"ES256", "RS256", "EdDSA"})
_jwk_clients: dict[str, jwt.PyJWKClient] = {}


def _get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    """Returns a cached PyJWKClient instance for the configured Supabase JWKS URL."""
    client = _jwk_clients.get(jwks_url)
    if client is None:
        client = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)
        _jwk_clients[jwks_url] = client
    return client


def _get_supabase_jwks_url() -> str:
    """Builds the Supabase Auth JWKS discovery endpoint URL."""
    base = settings.SUPABASE_URL.strip().rstrip("/")
    if not base or "localhost.supabase.co" in base:
        raise jwt.InvalidTokenError("Supabase URL not configured for asymmetric JWT verification")
    return f"{base}/auth/v1/.well-known/jwks.json"


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT using the configured HS256 secret or Supabase JWKS."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")
    if not isinstance(alg, str):
        raise jwt.InvalidAlgorithmError("JWT alg header must be a string")
    if alg == settings.JWT_ALGORITHM:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience="authenticated",
        )
    if alg in _ASYMMETRIC_ALGS:
        jwk_client = _get_jwk_client(_get_supabase_jwks_url())
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience="authenticated",
        )
    raise jwt.InvalidAlgorithmError(f"Unsupported JWT algorithm: {alg}")


def decode_access_token(token: str) -> TokenPayload:
    """Decodes and cryptographically validates a Supabase-issued JWT (HS256 or JWKS).

    Raises:
        HTTPException: 401 if token is expired, has an invalid signature,
                       or contains malformed claims.
    """
    try:
        payload = _decode_jwt_payload(token)
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    subject = payload.get("sub")
    email = payload.get("email")

    if not subject or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required subject or email claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(subject)
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user subject UUID format",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    user_metadata = payload.get("user_metadata")
    if user_metadata is not None and not isinstance(user_metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user_metadata claim in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_metadata = user_metadata or {}

    app_metadata = payload.get("app_metadata")
    if app_metadata is not None and not isinstance(app_metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed app_metadata claim in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    app_metadata = app_metadata or {}

    # Server-verified claims from app_metadata (populated by Supabase Custom
    # Access Token Auth Hook or SQL trigger from auth.identities upon OAuth login;
    # client-editable user_metadata is excluded to prevent authorization spoofing).
    raw_github_user = (
        app_metadata.get("github_username")
        or app_metadata.get("user_name")
        or app_metadata.get("preferred_username")
    )

    github_user: str | None = None
    if raw_github_user is not None:
        if not isinstance(raw_github_user, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed github_username claim in token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        cleaned_handle = raw_github_user.strip()
        if cleaned_handle:
            github_user = cleaned_handle

    return TokenPayload(
        sub=user_uuid,
        email=email,
        github_username=github_user,
        exp=payload.get("exp", 0),
        aud=payload.get("aud"),
        role=payload.get("role"),
        user_metadata=user_metadata,
        app_metadata=app_metadata,
    )


async def decode_access_token_async(token: str) -> TokenPayload:
    """Non-blocking wrapper validating HS256 synchronously and JWKS tokens off-thread."""
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    if not isinstance(alg, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if alg in _ASYMMETRIC_ALGS:
        return await anyio.to_thread.run_sync(decode_access_token, token)
    return decode_access_token(token)


async def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> TokenPayload:
    """FastAPI dependency validating the Bearer token without querying PostgreSQL."""
    return await decode_access_token_async(credentials.credentials)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency resolving the authenticated database User from the Bearer token.

    If the user does not yet exist in the local database (first-time login via Supabase),
    the user record is idempotently provisioned.
    """
    token_payload = await decode_access_token_async(credentials.credentials)

    stmt = select(User).where(User.id == token_payload.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Check if record with this email already exists to handle email-matched identities
        by_email_stmt = select(User).where(User.email == token_payload.email)
        by_email_res = await db.execute(by_email_stmt)
        existing_by_email = by_email_res.scalar_one_or_none()

        if existing_by_email is not None:
            user = existing_by_email
            if token_payload.github_username and not user.github_username:
                user.github_username = token_payload.github_username
                await db.commit()
                await db.refresh(user)
        else:
            user = User(
                id=token_payload.sub,
                email=token_payload.email,
                github_username=token_payload.github_username,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    else:
        updated = False
        if user.email != token_payload.email:
            user.email = token_payload.email
            updated = True
        if token_payload.github_username and not user.github_username:
            user.github_username = token_payload.github_username
            updated = True
        elif (
            token_payload.github_username
            and user.github_username
            and user.github_username != token_payload.github_username
        ):
            logger.warning(
                "rejected_github_handle_rebinding_attempt",
                user_id=str(user.id),
                current_handle=user.github_username,
                attempted_handle=token_payload.github_username,
            )
        if updated:
            await db.commit()
            await db.refresh(user)

    return user


async def verify_project_ownership(
    project_id_raw: str | uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Project:
    """Verifies that a project ID is valid and owned by the given user."""
    try:
        project_uuid = (
            project_id_raw if isinstance(project_id_raw, uuid.UUID) else uuid.UUID(project_id_raw)
        )
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        ) from err

    stmt = select(Project).where(Project.id == project_uuid, Project.user_id == user_id)
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )
    return project
