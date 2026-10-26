import uuid
from typing import List, Optional, Sequence

import structlog

from app.models.analysis import CodeSymbol
from app.schemas.chunk import ChunkType, CodeChunk

logger = structlog.get_logger(__name__)


def estimate_token_count(text: str) -> int:
    """Fast, deterministic token estimator approximating 4 characters per token."""
    cleaned = text.strip()
    if not cleaned:
        return 1
    return max(1, len(text) // 4)


def _subchunk_lines(
    file_id: uuid.UUID,
    lines: Sequence[str],
    start_line: int,
    end_line: int,
    language: str,
    chunk_type: ChunkType,
    symbol_id: Optional[uuid.UUID] = None,
    symbol_name: Optional[str] = None,
    max_tokens: int = 500,
    window_size: int = 40,
    overlap: int = 5,
) -> List[CodeChunk]:
    """Partitions a multi-line range into bounded chunks respecting token limits."""
    chunks: List[CodeChunk] = []
    total_range_lines = max(1, end_line - start_line + 1)

    # Check if the whole range fits into max_tokens
    full_text = "".join(lines[start_line - 1 : end_line])
    full_tokens = estimate_token_count(full_text)
    if full_tokens <= max_tokens:
        return [
            CodeChunk(
                file_id=file_id,
                symbol_id=symbol_id,
                symbol_name=symbol_name,
                chunk_type=chunk_type,
                content=full_text,
                start_line=start_line,
                end_line=end_line,
                token_count=full_tokens,
                language=language,
            )
        ]

    # Sliding window partition for oversized code blocks
    step = max(1, window_size - overlap)
    curr_offset = 0
    while curr_offset < total_range_lines:
        w_start = start_line + curr_offset
        w_end = min(end_line, w_start + window_size - 1)
        slice_text = "".join(lines[w_start - 1 : w_end])

        if slice_text.strip():
            tokens = estimate_token_count(slice_text)
            chunks.append(
                CodeChunk(
                    file_id=file_id,
                    symbol_id=symbol_id,
                    symbol_name=symbol_name,
                    chunk_type=ChunkType.BLOCK if chunk_type == ChunkType.SYMBOL else chunk_type,
                    content=slice_text,
                    start_line=w_start,
                    end_line=w_end,
                    token_count=tokens,
                    language=language,
                )
            )

        if w_end >= end_line:
            break
        curr_offset += step

    return chunks


def chunk_analyzed_file(
    file_id: uuid.UUID,
    file_path: str,
    content: str,
    language: str,
    symbols: Sequence[CodeSymbol],
    max_tokens: int = 500,
) -> List[CodeChunk]:
    """Partitions source code into syntax-aligned, bounded CodeChunk items.

    Aligns chunks with Tree-sitter function and class AST symbols, isolates module-level
    headers, and gracefully handles non-code or symbol-less files.
    """
    if not content or not content.strip():
        return []

    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    # 1. Fallback for files without extracted symbols (e.g. config, markdown, yaml)
    if not symbols:
        return _subchunk_lines(
            file_id=file_id,
            lines=lines,
            start_line=1,
            end_line=total_lines,
            language=language,
            chunk_type=ChunkType.FALLBACK,
            max_tokens=max_tokens,
            window_size=50,
            overlap=10,
        )

    # 2. Sort symbols by start_line ascending
    sorted_symbols = sorted(symbols, key=lambda s: (s.start_line, s.end_line))

    # Deduplicate nested symbols if parent symbol already fits within max_tokens
    filtered_symbols: List[CodeSymbol] = []
    for sym in sorted_symbols:
        # Check if enclosed by an existing symbol in filtered_symbols
        enclosing = next(
            (
                parent
                for parent in filtered_symbols
                if parent.start_line <= sym.start_line and parent.end_line >= sym.end_line
            ),
            None,
        )
        if enclosing:
            enclosing_text = "".join(lines[enclosing.start_line - 1 : enclosing.end_line])
            if estimate_token_count(enclosing_text) <= max_tokens:
                # Parent fits completely; no need to separately chunk child method
                continue
        filtered_symbols.append(sym)

    chunks: List[CodeChunk] = []

    # 3. Module Header (lines before the first symbol)
    first_sym = filtered_symbols[0]
    if first_sym.start_line > 1:
        header_text = "".join(lines[: first_sym.start_line - 1])
        if header_text.strip():
            header_tokens = estimate_token_count(header_text)
            chunks.append(
                CodeChunk(
                    file_id=file_id,
                    chunk_type=ChunkType.MODULE_HEADER,
                    content=header_text,
                    start_line=1,
                    end_line=first_sym.start_line - 1,
                    token_count=header_tokens,
                    language=language,
                )
            )

    # 4. Symbol and Inter-Symbol Processing
    for i, sym in enumerate(filtered_symbols):
        # Extract inter-symbol gap if previous symbol ended before this one starts
        if i > 0:
            prev_sym = filtered_symbols[i - 1]
            if sym.start_line > prev_sym.end_line + 1:
                gap_start = prev_sym.end_line + 1
                gap_end = sym.start_line - 1
                gap_text = "".join(lines[gap_start - 1 : gap_end])
                if gap_text.strip():
                    gap_tokens = estimate_token_count(gap_text)
                    chunks.append(
                        CodeChunk(
                            file_id=file_id,
                            chunk_type=ChunkType.BLOCK,
                            content=gap_text,
                            start_line=gap_start,
                            end_line=gap_end,
                            token_count=gap_tokens,
                            language=language,
                        )
                    )

        # Chunk the symbol itself
        sym_chunks = _subchunk_lines(
            file_id=file_id,
            lines=lines,
            start_line=sym.start_line,
            end_line=min(total_lines, sym.end_line),
            language=language,
            chunk_type=ChunkType.SYMBOL,
            symbol_id=sym.id,
            symbol_name=sym.name,
            max_tokens=max_tokens,
        )
        chunks.extend(sym_chunks)

    # 5. Trailing lines after the last symbol
    last_sym = filtered_symbols[-1]
    if last_sym.end_line < total_lines:
        tail_start = last_sym.end_line + 1
        tail_end = total_lines
        tail_text = "".join(lines[tail_start - 1 : tail_end])
        if tail_text.strip():
            tail_tokens = estimate_token_count(tail_text)
            chunks.append(
                CodeChunk(
                    file_id=file_id,
                    chunk_type=ChunkType.BLOCK,
                    content=tail_text,
                    start_line=tail_start,
                    end_line=tail_end,
                    token_count=tail_tokens,
                    language=language,
                )
            )

    logger.debug(
        "file_chunked_success",
        file_path=file_path,
        symbol_count=len(symbols),
        chunk_count=len(chunks),
    )
    return chunks
