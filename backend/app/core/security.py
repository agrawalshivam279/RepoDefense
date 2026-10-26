import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.project import User
from app.schemas.auth import TokenPayload

security_scheme = HTTPBearer(
    auto_error=True,
    description="Supabase JWT Bearer Token",
)


def decode_access_token(token: str) -> TokenPayload:
    """Decodes and cryptographically validates a Supabase-issued JWT.

    Raises:
        HTTPException: 401 if token is expired, has an invalid signature,
                       or contains malformed claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except jwt.InvalidTokenError as err:
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

    return TokenPayload(
        sub=user_uuid,
        email=email,
        exp=payload.get("exp", 0),
        aud=payload.get("aud"),
        role=payload.get("role"),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency resolving the authenticated database User from the Bearer token.

    If the user does not yet exist in the local database (first-time login via Supabase),
    the user record is idempotently provisioned.
    """
    token_payload = decode_access_token(credentials.credentials)

    stmt = select(User).where(User.id == token_payload.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(id=token_payload.sub, email=token_payload.email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif user.email != token_payload.email:
        user.email = token_payload.email
        await db.commit()
        await db.refresh(user)

    return user
