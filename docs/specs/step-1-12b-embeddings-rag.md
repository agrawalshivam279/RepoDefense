# Technical Specification: Step 1.12b — Local all-MiniLM-L6-v2 Embeddings & pgvector HNSW Retrieval Pipeline

**Phase:** Phase 2 — Analysis & Vectorization (The Brain)  
**Step ID:** `1.12b`  
**Feature Slug:** `step-1-12b-embeddings-rag`  
**Git Branch:** `feat/step-1-12b-embeddings-rag`  
**Target Completion Date:** 2026-10-27  
**Status:** In Progress  

---

## 1. Architectural Context & Goldilocks Scoping

### 1.1 Background & Strategic Intent
Following the completion of **Step 1.12a** (AST-Aware Code Chunking Engine), repository source files can be partitioned into granular, semantically intact code chunks ($\le 500$ tokens) aligned with Tree-sitter function and class boundaries. 

Per **Gemini.md Section 3 & 6**:
- RepoDefense uses local embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`) producing 384-dimensional dense vectors with zero external API cost and zero rate-limiting risk.
- Vectors are stored directly in PostgreSQL 17 via `pgvector` (`code_embeddings` table) indexed with an HNSW cosine distance index (`idx_code_embeddings_hnsw`).
- Retrieval queries calculate cosine distance (`<=>` operator) joined against relational tables (`analyzed_files`, `projects`) with ACID consistency.

### 1.2 Goldilocks Scope Boundary
To preserve the 5-Gate Goldilocks Task Granularity Standard ($\le 4$ target files, $\le 300$ LOC/file, $\ge 40\%$ context headroom):
- **In Scope**:
  1. Add `sentence-transformers` to `backend/pyproject.toml`.
  2. Define Pydantic request/response schemas for vector retrieval (`backend/app/schemas/embedding.py`).
  3. Implement local `SentenceTransformer` loader and embedding generator (`backend/app/analyzers/embeddings.py`) with lazy loading and singleton caching.
  4. Implement `embed_and_persist_project_chunks` batching chunk generation and bulk-inserting `CodeEmbedding` rows into PostgreSQL 17.
  5. Implement `retrieve_relevant_chunks` executing pgvector cosine distance queries with top-k ranking and similarity scoring.
  6. Integrate Stage 5 (Embeddings & Vectorization) into ARQ clone worker (`backend/app/workers/cloner.py`).
  7. Hermetic unit and integration tests (`backend/tests/test_embeddings.py`) mocking model weights for fast offline execution and live database retrieval testing.
- **Out of Scope (Deferred to Future Steps)**:
  - Phase 3 LLM question formulation (`Milestone 1.13`).
  - Active interview state machine execution (`Milestone 1.14`).

---

## 2. Target Files & Line Count Budget

| Target File | Purpose | Max LOC |
| :--- | :--- | :--- |
| `backend/pyproject.toml` | Add `sentence-transformers` dependency | ~65 LOC |
| `backend/app/schemas/embedding.py` | Pydantic RAG query & retrieved chunk contracts | $\le 60$ LOC |
| `backend/app/analyzers/embeddings.py` | SentenceTransformer loader, batch embedder, persister, and pgvector cosine retriever | $\le 250$ LOC |
| `backend/app/workers/cloner.py` | Integrate Stage 5 into repository cloning and analysis pipeline | $\le 290$ LOC |
| `backend/tests/test_embeddings.py` | Hermetic unit & database retrieval tests | $\le 250$ LOC |

---

## 3. Data Contracts & Schemas

### 3.1 Pydantic Schemas (`backend/app/schemas/embedding.py`)

```python
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class RetrievalQuery(BaseModel):
    """Query parameters for semantic code retrieval."""
    model_config = ConfigDict(frozen=True)

    project_id: uuid.UUID
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)
    file_id: Optional[uuid.UUID] = None

class RetrievedChunk(BaseModel):
    """A code chunk retrieved via pgvector cosine distance search."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    file_path: str
    symbol_id: Optional[uuid.UUID] = None
    chunk_content: str
    similarity: float = Field(ge=0.0, le=1.0)
    token_count: int
```

---

## 4. Core Implementation Sequence

### 4.1 Dependency Addition
Add `sentence-transformers>=3.0.0` to `backend/pyproject.toml` under `dependencies`.

### 4.2 Embedding Analyzer (`backend/app/analyzers/embeddings.py`)
1. **Lazy Model Singleton**:
   ```python
   _MODEL = None
   def get_embedding_model():
       global _MODEL
       if _MODEL is None:
           from sentence_transformers import SentenceTransformer
           _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
       return _MODEL
   ```
2. **Batch Embedding Generator**:
   ```python
   def generate_embeddings(texts: Sequence[str]) -> List[List[float]]:
       if not texts:
           return []
       model = get_embedding_model()
       embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
       return embeddings.tolist()
   ```
3. **Chunk Batch Persistence**:
   `embed_and_persist_project_chunks(session: AsyncSession, project_id: uuid.UUID) -> int`:
   - Queries all `AnalyzedFile` rows for `project_id`.
   - Also queries all `CodeSymbol` rows for `project_id`.
   - Chunks files using `chunk_analyzed_file`.
   - Batches chunk texts for embedding generation.
   - Cleans old embeddings for project files and bulk-inserts new `CodeEmbedding` records with `Vector(384)`.
4. **pgvector Cosine Retrieval**:
   `retrieve_relevant_chunks(session: AsyncSession, query_params: RetrievalQuery) -> List[RetrievedChunk]`:
   - Encodes query string into 384-dimensional normalized vector.
   - Executes pgvector cosine distance `<=>` query:
     ```python
     distance_col = CodeEmbedding.embedding.cosine_distance(query_vector)
     similarity_col = (1.0 - distance_col).label("similarity")
     stmt = (
         select(CodeEmbedding, AnalyzedFile.path, similarity_col)
         .join(AnalyzedFile, CodeEmbedding.file_id == AnalyzedFile.id)
         .where(AnalyzedFile.project_id == query_params.project_id)
     )
     if query_params.file_id:
         stmt = stmt.where(CodeEmbedding.file_id == query_params.file_id)
     stmt = stmt.order_by(distance_col.asc()).limit(query_params.top_k)
     ```
   - Formats and returns `List[RetrievedChunk]`.

### 4.3 Cloner Background Worker Integration (`backend/app/workers/cloner.py`)
- Insert **Stage 5: Vector Embeddings & Code Chunk Persistence** after Evidence extraction.
- Record `chunk_count` and `embedding_count` in `RepositorySnapshot.summary`.

---

## 5. Security & Invariant Checklist

- [x] **Zero Arbitrary Code Execution**: Code is strictly tokenized and encoded; no `eval()` or runtime execution.
- [x] **Strict 384-Dimension Vector Constraint**: Matches pgvector `Vector(384)` and HNSW index in PostgreSQL 17.
- [x] **Parameterized Queries**: All SQLAlchemy queries use parameterized binds; zero SQL injection risk.
- [x] **Tenancy & Isolation**: All vector searches require `project_id` scoping to prevent cross-tenant data leakage.
- [x] **300 LOC Ceiling**: All files strictly adhere to $\le 300$ lines.
- [x] **Offline Test Hermeticity**: Unit tests mock the embedding model to avoid test execution hangs and network dependencies.

---

## 6. Verification Criteria

1. `python -m ruff check backend/app` reports zero errors.
2. `python -m pytest backend/tests/test_embeddings.py -v` passes 100%.
3. Full backend test suite passes $\ge 95$ tests.
4. `powershell -Command "cd frontend; npx tsc --noEmit"` passes cleanly.
5. All new files are strictly under 300 LOC and 100 characters per line.
