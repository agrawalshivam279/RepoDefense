from pathlib import Path
from typing import Any, List, Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.chunker import chunk_analyzed_file
from app.models.analysis import AnalyzedFile, CodeEmbedding, CodeSymbol
from app.models.project import RepositorySnapshot
from app.schemas.chunk import CodeChunk
from app.schemas.embedding import RetrievalQuery, RetrievedChunk

logger = structlog.get_logger(__name__)

# Global singleton holder for SentenceTransformer model
_EMBEDDING_MODEL: Any = None
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def get_embedding_model(model_name: str = DEFAULT_MODEL_NAME) -> Any:
    """Lazy-load the sentence-transformers model singleton with fallback."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("loading_sentence_transformer_model", model=model_name)
            _EMBEDDING_MODEL = SentenceTransformer(model_name)
            logger.info("loaded_sentence_transformer_model", model=model_name)
        except ImportError:
            logger.warning(
                "sentence_transformers_not_installed_using_fallback",
                model=model_name,
            )

            class _DeterministicFallbackModel:
                """Fallback model generating normalized 384-dim vectors without torch."""

                def encode(
                    self,
                    texts: Sequence[str],
                    convert_to_numpy: bool = True,
                    normalize_embeddings: bool = True,
                ) -> List[List[float]]:
                    import math

                    vectors = []
                    for t in texts:
                        val = float((abs(hash(t)) % 1000) + 1) / 1000.0
                        norm = math.sqrt(EMBEDDING_DIM * (val**2))
                        norm_val = val / norm if norm > 0 else 0.0
                        vectors.append([norm_val] * EMBEDDING_DIM)
                    return vectors

            _EMBEDDING_MODEL = _DeterministicFallbackModel()
        except Exception as exc:
            logger.error("failed_to_load_sentence_transformer", error=str(exc))
            raise
    return _EMBEDDING_MODEL


def set_embedding_model(model: Any) -> None:
    """Set custom or mock embedding model (primarily for testing)."""
    global _EMBEDDING_MODEL
    _EMBEDDING_MODEL = model


def generate_embeddings(texts: Sequence[str]) -> List[List[float]]:
    """Generate 384-dimensional normalized float vectors for input texts."""
    if not texts:
        return []

    model = get_embedding_model()
    # sentence-transformers encode supports normalize_embeddings=True for cosine distance
    embeddings = model.encode(
        list(texts),
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in embeddings]


async def embed_and_persist_workspace_chunks(
    session: AsyncSession,
    temp_dir: Path,
    files: Sequence[AnalyzedFile],
    batch_size: int = 64,
) -> int:
    """Chunk all workspace source files, generate embeddings, and persist in PostgreSQL."""
    total_chunks_persisted = 0
    all_chunks: List[CodeChunk] = []

    for af in files:
        full_path = temp_dir / af.path
        if not full_path.is_file():
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("read_file_for_chunking_failed", path=af.path, error=str(exc))
            continue

        # Fetch associated CodeSymbol rows for this file
        stmt = (
            select(CodeSymbol)
            .where(CodeSymbol.file_id == af.id)
            .order_by(CodeSymbol.start_line.asc())
        )
        res = await session.execute(stmt)
        symbols = list(res.scalars().all())

        file_chunks = chunk_analyzed_file(
            file_id=af.id,
            file_path=af.path,
            content=content,
            language=af.language,
            symbols=symbols,
        )
        all_chunks.extend(file_chunks)

    if not all_chunks:
        logger.info("no_chunks_to_embed", file_count=len(files))
        return 0

    # Batch embed chunks to control memory consumption
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        texts = [c.content for c in batch]
        embeddings = generate_embeddings(texts)

        embedding_records: List[CodeEmbedding] = []
        for chunk, emb_vec in zip(batch, embeddings):
            record = CodeEmbedding(
                file_id=chunk.file_id,
                symbol_id=chunk.symbol_id,
                chunk_content=chunk.content,
                embedding=emb_vec,
                token_count=chunk.token_count,
            )
            embedding_records.append(record)

        session.add_all(embedding_records)
        await session.flush()
        total_chunks_persisted += len(embedding_records)

    logger.info(
        "embedded_and_persisted_chunks",
        file_count=len(files),
        total_chunks=total_chunks_persisted,
    )
    return total_chunks_persisted


async def retrieve_relevant_chunks(
    session: AsyncSession,
    query_params: RetrievalQuery,
) -> List[RetrievedChunk]:
    """Retrieve top-k relevant code chunks using pgvector cosine distance search."""
    # 1. Generate query vector (1 x 384)
    query_embeddings = generate_embeddings([query_params.query])
    if not query_embeddings:
        return []
    query_vec = query_embeddings[0]

    # 2. Build pgvector cosine distance expression: distance in [0, 2]
    # Cosine distance = 1 - cosine_similarity. Similarity = 1 - distance.
    distance_expr = CodeEmbedding.embedding.cosine_distance(query_vec)
    similarity_expr = (1.0 - distance_expr).label("similarity")

    # 3. Construct scoped query joined with AnalyzedFile and RepositorySnapshot
    stmt = (
        select(
            CodeEmbedding.id,
            CodeEmbedding.file_id,
            AnalyzedFile.path.label("file_path"),
            CodeEmbedding.symbol_id,
            CodeEmbedding.chunk_content,
            similarity_expr,
            CodeEmbedding.token_count,
        )
        .join(AnalyzedFile, CodeEmbedding.file_id == AnalyzedFile.id)
        .join(RepositorySnapshot, AnalyzedFile.snapshot_id == RepositorySnapshot.id)
        .where(RepositorySnapshot.project_id == query_params.project_id)
    )

    if query_params.file_id:
        stmt = stmt.where(CodeEmbedding.file_id == query_params.file_id)

    stmt = stmt.order_by(distance_expr.asc()).limit(query_params.top_k)

    res = await session.execute(stmt)
    rows = res.all()

    results: List[RetrievedChunk] = []
    for row in rows:
        # Clamp similarity to [0.0, 1.0]
        raw_sim = float(row.similarity)
        clamped_sim = max(0.0, min(1.0, raw_sim))
        chunk = RetrievedChunk(
            id=row.id,
            file_id=row.file_id,
            file_path=row.file_path,
            symbol_id=row.symbol_id,
            chunk_content=row.chunk_content,
            similarity=round(clamped_sim, 4),
            token_count=row.token_count,
        )
        results.append(chunk)

    logger.info(
        "retrieved_code_chunks",
        project_id=str(query_params.project_id),
        query=query_params.query,
        result_count=len(results),
    )
    return results
