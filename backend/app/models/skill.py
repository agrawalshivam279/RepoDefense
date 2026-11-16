"""SQLAlchemy 2.0 async models for candidate skills and weakness tracking."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project, User


class UserSkill(Base, TimestampMixin):
    """Aggregated technical proficiency and track record for a candidate on a specific topic."""

    __tablename__ = "user_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    proficiency_score: Mapped[float] = mapped_column(
        Float,
        default=50.0,
        nullable=False,
    )
    total_evaluations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    passed_evaluations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_evaluations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="skills",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "category",
            "topic",
            name="uq_user_skills_user_category_topic",
        ),
        Index(
            "ix_user_skills_user_proficiency",
            "user_id",
            "proficiency_score",
        ),
    )


class CandidateWeakness(Base, TimestampMixin):
    """Explicit architectural deficiency or gap identified during a simulation session."""

    __tablename__ = "candidate_weaknesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    simulation_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(16),
        default="major",
        nullable=False,
    )
    question_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    candidate_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    topic_embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(384),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="weaknesses",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="weaknesses",
    )

    @property
    def has_embedding(self) -> bool:
        """Whether this weakness record has an associated topic vector embedding."""
        return self.topic_embedding is not None

    __table_args__ = (
        Index(
            "ix_candidate_weaknesses_user_resolved_severity",
            "user_id",
            "resolved",
            "severity",
        ),
        Index(
            "ix_candidate_weaknesses_project_mode",
            "project_id",
            "simulation_mode",
        ),
    )
