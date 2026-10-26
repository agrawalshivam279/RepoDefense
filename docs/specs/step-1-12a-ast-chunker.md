# 📄 Technical Specification: Step 1.12a: AST-Aware Code Chunking Engine

> **Step ID**: `Step 1.12a`  
> **Feature Title**: AST-Aware Code Chunking Engine  
> **Target Module**: `backend/app/analyzers/chunker.py`, `backend/app/schemas/chunk.py`  
> **Git Feature Branch**: `feat/step-1-12a-ast-chunker`  
> **Status**: 📋 Ready for Implementation  
> **Created**: 2026-10-27  

---

## 1. Executive Summary

Per **Gemini.md** (Section 1 & 4) and **eval_rag** (`.agents/skills/eval_rag/SKILL.md`), RepoDefense's retrieval-augmented defense mechanism requires code to be chunked along **AST syntax boundaries** rather than arbitrary token or character counts. Blind token splitting cuts functions in half, separates docstrings from signatures, and injects malformed syntax into the LLM context.

Milestone 1.12 is sub-sliced under the Goldilocks standard into:
- **Step 1.12a**: AST-Aware Code Chunking Engine (This step — symbol boundary parsing, header isolation, sub-chunking, and data contracts).
- **Step 1.12b**: Local `all-MiniLM-L6-v2` Embeddings & pgvector HNSW Retrieval Pipeline.

Step 1.12a delivers the deterministic chunking engine that takes an `AnalyzedFile`, its source content, and its extracted `CodeSymbol` records (from Milestone 1.7), and partitions the file into cohesive, syntax-intact `CodeChunk` objects ($\le 500$ tokens) with exact line range traceability and symbol ID linkages.

---

## 2. Dependencies & Prerequisites

- **Depends on**:
  - `Milestone 1.6`: `AnalyzedFile` model and file metadata extraction.
  - `Milestone 1.7`: `CodeSymbol` model with `symbol_type`, `start_line`, `end_line`, and `name`.
  - `ADR-005`: Local embeddings architecture in `flashback.md`.
- **Blocked by**: None.
- **Tech Stack Invariant**: Zero new external dependencies. Operates purely with Python standard library and existing Pydantic v2 schemas.

---

## 3. 🛡️ Security, Grounding & Invariants Impact

- [x] **Zero Code Execution**: Static analysis only. Operates on source strings and database records without compiling or running user code.
- [x] **Exact Syntax Grounding**: Chunks preserve 1-indexed `start_line` and `end_line` coordinates and link to `symbol_id`.
- [x] **Token Bounding**: Chunks are constrained to $\le 500$ tokens to guarantee compatibility with `all-MiniLM-L6-v2` (which has a 512-token context limit).
- [x] **File Length Limit**: All files strictly adhere to $\le 300$ LOC and $\le 100$ characters per line.

---

## 4. 🧠 Sequential Thinking Strategy

Chunking arbitrary source code requires multi-branch reasoning to avoid edge-case failures:

1. **Symbol Alignment**:
   - Symbols extracted by Tree-sitter provide 1-indexed `start_line` and `end_line`.
   - Nested methods within classes: If a class has member methods, methods should be distinct symbol chunks or grouped if small.
2. **Module Header & Gaps**:
   - Lines prior to the first symbol contain critical architectural context: `import` statements, module-level docstrings, global constants.
   - These are isolated as `ChunkType.MODULE_HEADER`.
3. **Large Symbol Sub-Chunking**:
   - If a function or class exceeds 500 tokens (e.g. 150 lines of complex logic), blind splitting is avoided. Instead, it is partitioned along statement line windows (e.g. 40 lines with 5-line overlap) with `ChunkType.BLOCK` retaining `symbol_id` and `symbol_name`.
4. **Fallback for Non-Symbol Files**:
   - Config files, JSON, YAML, and Markdown files have no AST symbols.
   - They use line-based sliding windows (50 lines with 10-line overlap).

---

## 5. Data Contracts & Interfaces

### 5.1 Pydantic Schemas (`backend/app/schemas/chunk.py`)

```python
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ChunkType(str, Enum):
    """Classification of code chunk origin and structural role."""

    SYMBOL = "symbol"
    MODULE_HEADER = "header"
    BLOCK = "block"
    FALLBACK = "fallback"


class CodeChunk(BaseModel):
    """Self-contained, AST-grounded code chunk for vectorization and retrieval."""

    file_id: uuid.UUID = Field(..., description="Parent AnalyzedFile UUID")
    symbol_id: Optional[uuid.UUID] = Field(None, description="Linked CodeSymbol UUID if applicable")
    symbol_name: Optional[str] = Field(None, description="Name of the enclosing symbol")
    chunk_type: ChunkType = Field(..., description="Structural classification of the chunk")
    content: str = Field(..., description="Exact code text slice")
    start_line: int = Field(..., ge=1, description="1-indexed starting line")
    end_line: int = Field(..., ge=1, description="1-indexed ending line")
    token_count: int = Field(..., ge=1, description="Estimated token count")
    language: str = Field(..., description="Programming language tag")

    model_config = ConfigDict(from_attributes=True)
```

---

## 6. Implementation Logic

### 6.1 Chunking Engine (`backend/app/analyzers/chunker.py`)

- **Token Estimator**:
  ```python
  def estimate_token_count(text: str) -> int:
      """Fast, deterministic token estimation (~4 chars per token, min 1)."""
      return max(1, len(text) // 4)
  ```

- **Core Function**:
  ```python
  def chunk_analyzed_file(
      file_id: uuid.UUID,
      file_path: str,
      content: str,
      language: str,
      symbols: Sequence[CodeSymbol],
      max_tokens: int = 500,
  ) -> list[CodeChunk]:
  ```

- **Algorithm**:
  1. Split `content` into 1-indexed lines: `lines = content.splitlines(keepends=True)`.
  2. If `symbols` is empty:
     - Apply sliding window: slices of up to 50 lines with 10-line overlap. Mark as `ChunkType.FALLBACK`.
  3. If `symbols` is present:
     - Sort symbols by `(start_line, end_line)`.
     - Filter out nested symbols whose boundaries are fully enclosed by a larger symbol (or treat classes and standalone functions as primary).
     - **Header**: If `first_symbol.start_line > 1`, slice lines `1` to `first_symbol.start_line - 1`. If content contains non-whitespace, yield `ChunkType.MODULE_HEADER`.
     - **Symbols**: For each symbol:
       - Extract lines `sym.start_line` to `sym.end_line`.
       - If `estimate_token_count(text) <= max_tokens`: yield `ChunkType.SYMBOL` with `symbol_id=sym.id` and `symbol_name=sym.name`.
       - If `estimate_token_count(text) > max_tokens`: sub-slice into blocks of 40 lines with 5-line overlap, marked as `ChunkType.BLOCK` with `symbol_id=sym.id`.
     - **Inter-Symbol Gaps**: Between `prev_sym.end_line + 1` and `next_sym.start_line - 1`. If non-empty, yield `ChunkType.BLOCK`.
     - **Trailing**: After `last_sym.end_line + 1` to end of file.

---

## 7. Step-by-Step Implementation Sequence

1. **Step A: Schema Definition**
   - Create `backend/app/schemas/chunk.py` with `ChunkType` and `CodeChunk`.
   - Re-export in `backend/app/schemas/__init__.py`.

2. **Step B: Chunking Engine**
   - Create `backend/app/analyzers/chunker.py` with `estimate_token_count` and `chunk_analyzed_file`.
   - Re-export in `backend/app/analyzers/__init__.py`.

3. **Step C: Test Suite**
   - Create `backend/tests/test_chunker.py` covering:
     - Token estimation.
     - Function/class symbol boundary preservation.
     - Module header isolation (imports/docstring).
     - Large symbol sub-chunking.
     - Non-symbol fallback window chunking.
     - Clean boundary line coordinate verification.

---

## 8. Verification & Acceptance Criteria

### Automated Test Command
```bash
pytest backend/tests/test_chunker.py -v
```

### Acceptance Checklist
- [ ] Functions and classes are extracted intact without mid-statement cuts.
- [ ] Chunks do not exceed `max_tokens` (default 500 tokens).
- [ ] All chunks include valid 1-indexed `start_line` and `end_line`.
- [ ] Every symbol chunk correctly links to `symbol_id`.
- [ ] Zero arbitrary code execution; 100% static logic.
- [ ] All files strictly $\le 300$ LOC and $\le 100$ characters per line.
- [ ] Full backend test suite passes cleanly.
