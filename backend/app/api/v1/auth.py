from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.project import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated user profile",
    description="Resolves and returns the authenticated user's profile from the Bearer JWT token.",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Returns the authenticated user record, synchronized with the local PostgreSQL database."""
    return UserResponse.model_validate(current_user)
