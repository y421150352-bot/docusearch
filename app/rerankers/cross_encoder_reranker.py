from functools import lru_cache
from pathlib import Path

from sentence_transformers import CrossEncoder

from app.config import (
    RERANKER_LOCAL_FILES_ONLY,
    RERANKER_MODEL_NAME,
    USE_RERANKER,
)


def _is_local_model_path(model_name: str) -> bool:
    model_path = Path(model_name)
    return model_path.is_absolute() or "\\" in model_name or "/" in model_name


def _with_empty_rerank_scores(chunks: list[dict]) -> list[dict]:
    fallback_chunks: list[dict] = []
    for chunk in chunks:
        fallback_chunk = chunk.copy()
        fallback_chunk["rerank_score"] = None
        fallback_chunks.append(fallback_chunk)
    return fallback_chunks


@lru_cache(maxsize=1)
def get_reranker_model() -> CrossEncoder | None:
    if not USE_RERANKER:
        return None

    model_path = Path(RERANKER_MODEL_NAME)
    if _is_local_model_path(RERANKER_MODEL_NAME) and not model_path.exists():
        print(
            ">>> RERANKER DISABLED OR MODEL PATH NOT FOUND: "
            f"{RERANKER_MODEL_NAME}"
        )
        return None

    try:
        return CrossEncoder(
            RERANKER_MODEL_NAME,
            local_files_only=RERANKER_LOCAL_FILES_ONLY,
        )
    except Exception as exc:
        print(f">>> RERANKER FAILED TO LOAD: {exc!r}")
        return None


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_n: int,
) -> list[dict]:
    if not chunks:
        return []

    fallback_chunks = _with_empty_rerank_scores(chunks)

    if not USE_RERANKER:
        return fallback_chunks

    model = get_reranker_model()
    if model is None:
        return fallback_chunks

    pairs = [(query, str(chunk.get("content", ""))) for chunk in chunks]
    try:
        scores = model.predict(pairs)
    except Exception as exc:
        print(f">>> RERANKER FAILED, fallback: {exc!r}")
        return fallback_chunks

    reranked_chunks: list[dict] = []
    for chunk, score in zip(chunks, scores):
        reranked_chunk = chunk.copy()
        reranked_chunk["rerank_score"] = float(score)
        reranked_chunks.append(reranked_chunk)

    reranked_chunks.sort(
        key=lambda item: item.get("rerank_score", float("-inf")),
        reverse=True,
    )
    print(">>> RERANKER: enabled")
    print(f">>> RERANKER: scored {len(reranked_chunks)} chunks")
    return reranked_chunks
