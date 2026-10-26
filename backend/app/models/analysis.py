import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AnalyzedFile(Base):
    """Cataloged source code file from an analyzed repository snapshot."""

    __tablename__ = "analyzed_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    total_lines: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    snapshot: Mapped["RepositorySnapshot"] = relationship(  # noqa: F821
        "RepositorySnapshot",
        back_populates="files",
    )
    symbols: Mapped[List["CodeSymbol"]] = relationship(
        "CodeSymbol",
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    embeddings: Mapped[List["CodeEmbedding"]] = relationship(
        "CodeEmbedding",
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CodeSymbol(Base):
    """Deterministic AST symbol extracted via Tree-sitter (function, class, endpoint)."""

    __tablename__ = "code_symbols"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyzed_files.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    symbol_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    start_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    end_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    signature: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    docstring: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    file: Mapped["AnalyzedFile"] = relationship(
        "AnalyzedFile",
        back_populates="symbols",
    )
    embeddings: Mapped[List["CodeEmbedding"]] = relationship(
        "CodeEmbedding",
        back_populates="symbol",
    )


class Dependency(Base):
    """Third-party library, package, or framework extracted from configuration files."""

    __tablename__ = "dependencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    source_file: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_dev: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project",
        back_populates="dependencies",
    )


class Evidence(Base):
    """Load-bearing architectural evidence item used for grounding interview defenses."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    start_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    end_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project",
        back_populates="evidence",
    )


class CodeEmbedding(Base):
    """384-dimensional vector embedding for code chunks, indexed with HNSW cosine distance."""

    __tablename__ = "code_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyzed_files.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_symbols.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    embedding = mapped_column(
        Vector(384),
        nullable=False,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    file: Mapped["AnalyzedFile"] = relationship(
        "AnalyzedFile",
        back_populates="embeddings",
    )
    symbol: Mapped[Optional["CodeSymbol"]] = relationship(
        "CodeSymbol",
        back_populates="embeddings",
    )

    __table_args__ = (
        Index(
            "idx_code_embeddings_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
