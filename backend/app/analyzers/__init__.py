"""Repository analyzers: scanning, AST, dependencies, history, evidence, and embeddings."""

from app.analyzers.architecture import (
    detect_architectural_risks,
    eval_clean_architecture,
    eval_event_driven,
    eval_layered_architecture,
    eval_modular_monolith,
    eval_mvc,
    get_confidence_tier,
    normalize_directory_tokens,
)
from app.analyzers.ast import (
    SymbolMetadata,
    extract_and_persist_file_symbols,
    extract_code_symbols,
    persist_code_symbols,
)
from app.analyzers.blame import (
    LineBlameInfo,
    compute_range_attribution,
    parse_file_blame,
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
from app.analyzers.diagram import (
    build_deterministic_mermaid_diagram,
    classify_tier,
    sanitize_node_id,
    sanitize_node_label,
    validate_mermaid_syntax,
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
    "ContributorStats",
    "DEFAULT_MODEL_NAME",
    "DependencyMetadata",
    "EMBEDDING_DIM",
    "FileMetadata",
    "GitCommitMetadata",
    "GitHistorySummary",
    "LineBlameInfo",
    "SymbolMetadata",
    "chunk_analyzed_file",
    "compute_range_attribution",
    "detect_architectural_risks",
    "build_deterministic_mermaid_diagram",
    "classify_tier",
    "sanitize_node_id",
    "sanitize_node_label",
    "validate_mermaid_syntax",
    "detect_language",
    "embed_and_persist_workspace_chunks",
    "estimate_token_count",
    "eval_clean_architecture",
    "eval_event_driven",
    "eval_layered_architecture",
    "eval_modular_monolith",
    "eval_mvc",
    "extract_and_persist_evidence",
    "extract_and_persist_file_symbols",
    "extract_code_symbols",
    "extract_evidence",
    "extract_file_dependencies",
    "extract_file_metadata",
    "extract_git_history",
    "generate_embeddings",
    "get_confidence_tier",
    "get_embedding_model",
    "normalize_directory_tokens",
    "parse_file_blame",
    "persist_analyzed_files",
    "persist_code_symbols",
    "persist_dependencies",
    "retrieve_relevant_chunks",
    "scan_workspace_files",
    "set_embedding_model",
]
