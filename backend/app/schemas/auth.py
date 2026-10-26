import uuid
from datetime import datetime
from typing import Union

from pydantic import BaseModel, ConfigDict, Field


class TokenPayload(BaseModel):
    """Decoded Supabase JWT claims payload."""

    sub: uuid.UUID = Field(description="User unique identifier (UUID)")
    email: str = Field(description="User email address")
    exp: int = Field(description="Token expiration timestamp (epoch seconds)")
    aud: Union[str, list[str], None] = Field(default=None, description="Audience claim")
    role: Union[str, None] = Field(default=None, description="Supabase user role")


class UserResponse(BaseModel):
    """Public user identity response payload."""

    id: uuid.UUID = Field(description="Unique user identifier")
    email: str = Field(description="User email address")
    created_at: datetime = Field(description="User creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)
