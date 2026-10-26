import uuid
from pathlib import Path
from typing import Optional, Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.ast.base import BaseASTParser, SymbolMetadata
from app.analyzers.ast.python import PythonASTParser
from app.analyzers.ast.typescript import TypeScriptASTParser
from app.models.analysis import AnalyzedFile, CodeSymbol

logger = structlog.get_logger(__name__)

# Registry of supported Tree-sitter AST language parsers
_PARSER_REGISTRY: dict[str, BaseASTParser] = {
    "Python": PythonASTParser(),
    "TypeScript": TypeScriptASTParser(),
    "JavaScript": TypeScriptASTParser(),
}


def get_ast_parser(language: str) -> Optional[BaseASTParser]:
    """Retrieves the Tree-sitter AST parser for the given canonical language."""
    return _PARSER_REGISTRY.get(language)


def extract_code_symbols(code_bytes: bytes, language: str) -> list[SymbolMetadata]:
    """Parses code bytes into symbols using the appropriate language AST parser.

    Returns an empty list if no parser is registered for the language.
    """
    parser = get_ast_parser(language)
    if not parser:
        return []
    return parser.parse(code_bytes)


async def persist_code_symbols(
    session: AsyncSession,
    file_id: uuid.UUID,
    symbols: Sequence[SymbolMetadata],
) -> list[CodeSymbol]:
    """Batch persists SymbolMetadata records as CodeSymbol rows in PostgreSQL.

    Args:
        session: Active asynchronous SQLAlchemy database session.
        file_id: Foreign key pointing to the parent AnalyzedFile.
        symbols: Sequence of extracted SymbolMetadata schemas.

    Returns:
        List of created CodeSymbol SQLAlchemy model instances.
    """
    records: list[CodeSymbol] = []
    for s in symbols:
        record = CodeSymbol(
            id=uuid.uuid4(),
            file_id=file_id,
            name=s.name,
            symbol_type=s.symbol_type,
            start_line=s.start_line,
            end_line=s.end_line,
            signature=s.signature,
            docstring=s.docstring,
        )
        records.append(record)

    session.add_all(records)
    await session.flush()
    logger.info(
        "code_symbols_persisted",
        file_id=str(file_id),
        symbol_count=len(records),
    )
    return records


async def extract_and_persist_file_symbols(
    session: AsyncSession,
    file: AnalyzedFile,
    file_path: Path,
) -> list[CodeSymbol]:
    """Reads a file from disk, parses its AST symbols, and persists them into PostgreSQL.

    Args:
        session: Active asynchronous SQLAlchemy session.
        file: AnalyzedFile record corresponding to the source file.
        file_path: Absolute filesystem path to the source file.

    Returns:
        List of created CodeSymbol records.
    """
    if not file_path.is_file():
        logger.warning("file_not_found_for_ast", path=str(file_path))
        return []

    try:
        code_bytes = file_path.read_bytes()
    except Exception as exc:
        logger.error("file_read_failed_for_ast", path=str(file_path), error=str(exc))
        return []

    symbols = extract_code_symbols(code_bytes, file.language)
    if not symbols:
        return []

    return await persist_code_symbols(session, file.id, symbols)


__all__ = [
    "BaseASTParser",
    "SymbolMetadata",
    "PythonASTParser",
    "TypeScriptASTParser",
    "get_ast_parser",
    "extract_code_symbols",
    "persist_code_symbols",
    "extract_and_persist_file_symbols",
]
