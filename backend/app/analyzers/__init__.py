"""Repository analyzers: scanning, AST, dependencies, history, evidence, and embeddings."""

from app.analyzers.ast import (
    SymbolMetadata,
    extract_and_persist_file_symbols,
    extract_code_symbols,
    persist_code_symbols,
)
from app.analyzers.chunker import (
    chunk_analyzed_file,
    estimate_token_count,
)
from app.analyzers.dependencies import (
    DependencyMetadata,
    extract_file_dependencies,
    persist_dependencies,
)
from app.analyzers.embeddings import (
    DEFAULT_MODEL_NAME,
    EMBEDDING_DIM,
    embed_and_persist_workspace_chunks,
    generate_embeddings,
    get_embedding_model,
    retrieve_relevant_chunks,
    set_embedding_model,
)
from app.analyzers.evidence import (
    extract_and_persist_evidence,
    extract_evidence,
)
from app.analyzers.git import (
    ContributorStats,
    GitCommitMetadata,
    GitHistorySummary,
    extract_git_history,
)
from app.analyzers.languages import detect_language
from app.analyzers.scanner import (
    FileMetadata,
    extract_file_metadata,
    persist_analyzed_files,
    scan_workspace_files,
)

__all__ = [
    "detect_language",
    "extract_file_metadata",
    "scan_workspace_files",
    "persist_analyzed_files",
    "FileMetadata",
    "SymbolMetadata",
    "DependencyMetadata",
    "extract_code_symbols",
    "persist_code_symbols",
    "extract_and_persist_file_symbols",
    "extract_file_dependencies",
    "persist_dependencies",
    "GitCommitMetadata",
    "ContributorStats",
    "GitHistorySummary",
    "extract_git_history",
    "extract_evidence",
    "extract_and_persist_evidence",
    "chunk_analyzed_file",
    "estimate_token_count",
    "DEFAULT_MODEL_NAME",
    "EMBEDDING_DIM",
    "get_embedding_model",
    "set_embedding_model",
    "generate_embeddings",
    "embed_and_persist_workspace_chunks",
    "retrieve_relevant_chunks",
]
