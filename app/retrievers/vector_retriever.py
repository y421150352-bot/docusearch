from collections import OrderedDict

import numpy as np
from qdrant_client import models

from app.config import (
    QDRANT_COLLECTION_NAME,
    RERANK_CANDIDATE_TOP_K,
    RERANK_TOP_N,
    TOP_K,
    USE_QDRANT_RETRIEVAL,
    USE_RERANKER,
)
from app.rerankers import rerank_chunks
from app.retrievers.embedding_client import encode_query
from app.retrievers.qdrant_client import get_qdrant_client
from app.retrievers.qdrant_indexer import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from app.retrievers.sparse_encoder import encode_query_sparse
from app.services.document_chunk_service import get_document_chunks_by_ids


def _parse_chunk_index(chunk_id: str) -> int:
    try:
        return int(chunk_id.split("_c")[-1])
    except (ValueError, IndexError):
        return -1


def _is_too_close(candidate: dict, selected: dict) -> bool:
    same_doc = candidate.get("document_name") == selected.get("document_name")
    same_page = candidate.get("page_number") == selected.get("page_number")
    candidate_idx = _parse_chunk_index(str(candidate.get("chunk_id", "")))
    selected_idx = _parse_chunk_index(str(selected.get("chunk_id", "")))
    if candidate_idx == -1 or selected_idx == -1:
        return False
    return same_doc and same_page and abs(candidate_idx - selected_idx) <= 1


def search_qdrant_index(
    query: str,
    owner_id: int | None,
    top_k: int = TOP_K,
    document_name: str | None = None,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    query_embedding = np.asarray(encode_query(query), dtype="float32")[0].tolist()
    filters = []
    if owner_id is not None:
        filters.append(
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=int(owner_id)),
            )
        )
    if document_name:
        filters.append(
            models.FieldCondition(
                key="document_name",
                match=models.MatchValue(value=document_name),
            )
        )
    query_filter = models.Filter(must=filters) if filters else None
    prefetch_limit = max(top_k * 4, 20)
    prefetch = [
        models.Prefetch(
            query=query_embedding,
            using=DENSE_VECTOR_NAME,
            filter=query_filter,
            limit=prefetch_limit,
        ),
        models.Prefetch(
            query=encode_query_sparse(query),
            using=SPARSE_VECTOR_NAME,
            filter=query_filter,
            limit=prefetch_limit,
        ),
    ]
    response = get_qdrant_client().query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=max(top_k * 3, top_k),
        with_payload=True,
    )

    point_ids = [int(point.id) for point in response.points]
    chunk_map = get_document_chunks_by_ids(point_ids)
    results: list[dict] = []
    for point in response.points:
        chunk_row = chunk_map.get(int(point.id))
        if chunk_row is None:
            continue
        chunk = {
            "chunk_id": chunk_row.chunk_id,
            "document_name": chunk_row.document_name,
            "page_number": chunk_row.page_number,
            "content": chunk_row.content,
            "owner_id": point.payload.get("owner_id") if point.payload else None,
        }
        chunk["score"] = round(float(point.score), 4)
        chunk["retrieval_type"] = "qdrant_dense_sparse_rrf"

        if any(_is_too_close(chunk, existing) for existing in results):
            continue

        results.append(chunk)
        if len(results) >= top_k:
            break

    return results


def _candidate_key(chunk: dict) -> str:
    chunk_id = str(chunk.get("chunk_id", "")).strip()
    if chunk_id:
        return chunk_id
    document_name = str(chunk.get("document_name", "")).strip()
    page_number = str(chunk.get("page_number", "")).strip()
    content = str(chunk.get("content", "")).strip()
    return f"{document_name}::{page_number}::{content[:160]}"


def _merge_chunk(existing: dict, incoming: dict) -> dict:
    merged = existing.copy()
    merged["score"] = max(
        float(existing.get("score", float("-inf"))),
        float(incoming.get("score", float("-inf"))),
    )
    existing_type = str(existing.get("retrieval_type", "unknown"))
    incoming_type = str(incoming.get("retrieval_type", "unknown"))
    if existing_type == incoming_type:
        merged["retrieval_type"] = existing_type
    else:
        merged["retrieval_type"] = "hybrid"
    if "rerank_score" in incoming and incoming.get("rerank_score") is not None:
        merged["rerank_score"] = incoming.get("rerank_score")
    return merged


def merge_retrieval_candidates(*candidate_groups: list[dict]) -> list[dict]:
    merged_map: OrderedDict[str, dict] = OrderedDict()
    for group in candidate_groups:
        for chunk in group:
            key = _candidate_key(chunk)
            if key in merged_map:
                merged_map[key] = _merge_chunk(merged_map[key], chunk)
            else:
                normalized_chunk = chunk.copy()
                normalized_chunk.setdefault("rerank_score", None)
                merged_map[key] = normalized_chunk
    return list(merged_map.values())


def hybrid_search_candidates(
    query: str,
    owner_id: int | None,
    document_name: str | None = None,
    candidate_top_k: int = RERANK_CANDIDATE_TOP_K,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    if USE_RERANKER:
        candidate_top_k = max(candidate_top_k, RERANK_TOP_N)

    if USE_QDRANT_RETRIEVAL:
        try:
            return search_qdrant_index(
                query=query,
                owner_id=owner_id,
                top_k=candidate_top_k,
                document_name=document_name,
            )
        except Exception as exc:
            print(f">>> QDRANT HYBRID SEARCH FAILED: {exc}")
    return []


def rerank_or_fallback(
    query: str,
    candidates: list[dict],
    top_n: int,
) -> list[dict]:
    if not candidates:
        return []
    if not USE_RERANKER:
        print(">>> RERANKER: disabled")
        return candidates[:top_n]

    try:
        reranked = rerank_chunks(
            query=query,
            chunks=candidates,
            top_n=top_n,
        )
        if any(chunk.get("rerank_score") is not None for chunk in reranked):
            return reranked[:top_n]
        return candidates[:top_n]
    except Exception as exc:
        print(f">>> RERANKER FAILED, fallback: {exc}")
        return candidates[:top_n]


def _group_chunks_by_document(candidates: list[dict], chunks_per_doc: int) -> OrderedDict[str, list[dict]]:
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for candidate in candidates:
        document_name = candidate.get("document_name")
        if not document_name:
            continue
        selected_chunks = grouped.setdefault(document_name, [])
        if len(selected_chunks) >= chunks_per_doc:
            continue
        selected_chunks.append(
            {
                "chunk_id": candidate.get("chunk_id"),
                "document_name": candidate.get("document_name"),
                "page_number": candidate.get("page_number"),
                "content": candidate.get("content", ""),
                "score": candidate.get("score", 0),
                "rerank_score": candidate.get("rerank_score"),
                "retrieval_type": candidate.get("retrieval_type", "unknown"),
            }
        )
    return grouped


def _select_diverse_chunks(
    candidates: list[dict],
    max_docs: int,
    chunks_per_doc: int,
) -> list[dict]:
    grouped = _group_chunks_by_document(candidates, chunks_per_doc=chunks_per_doc)
    selected_documents = list(grouped.items())[:max_docs]
    if not selected_documents:
        return []

    balanced_results: list[dict] = []
    for chunk_index in range(chunks_per_doc):
        for _, chunks in selected_documents:
            if chunk_index < len(chunks):
                balanced_results.append(chunks[chunk_index])
    return balanced_results


def retrieve_multi_document_chunks(
    query: str,
    owner_id: int,
    max_docs: int = 4,
    chunks_per_doc: int = 3,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    candidate_k = max(RERANK_CANDIDATE_TOP_K, max_docs * chunks_per_doc * 4)
    candidates = hybrid_search_candidates(
        query=query,
        owner_id=owner_id,
        document_name=None,
        candidate_top_k=candidate_k,
    )
    reranked_candidates = rerank_or_fallback(
        query=query,
        candidates=candidates,
        top_n=max(candidate_k, RERANK_TOP_N),
    )
    selected_results = _select_diverse_chunks(
        reranked_candidates,
        max_docs=max_docs,
        chunks_per_doc=chunks_per_doc,
    )
    return selected_results
