import json
import os
from datetime import datetime

import numpy as np
from qdrant_client import models
from sqlmodel import Session, select

from app.config import (
    EMBEDDING_META_FILE,
    EMBEDDING_MODEL_NAME,
    QDRANT_COLLECTION_NAME,
)
from app.retrievers.embedding_client import encode_texts
from app.retrievers.qdrant_client import get_qdrant_client
from app.retrievers.sparse_encoder import encode_document_sparse
from app.services.document_chunk_service import list_document_chunks
from app.db.database import engine
from app.models.document_model import DocumentRecord


DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "bm25"
UPSERT_BATCH_SIZE = 128


def _delete_orphan_points(client, expected_point_ids: set[int]) -> int:
    actual_point_ids: set[int] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=256,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        actual_point_ids.update(int(point.id) for point in points)
        if offset is None:
            break

    orphan_point_ids = sorted(actual_point_ids - expected_point_ids)
    if orphan_point_ids:
        client.delete(
            collection_name=QDRANT_COLLECTION_NAME,
            points_selector=models.PointIdsList(points=orphan_point_ids),
            wait=True,
        )
    return len(orphan_point_ids)


def _atomic_write_json(target_path, payload: dict) -> None:
    tmp_path = target_path.with_name(f"{target_path.name}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as file_object:
        json.dump(payload, file_object, ensure_ascii=False, indent=2)
    os.replace(tmp_path, target_path)


def build_qdrant_index_from_chunks() -> int:
    chunks = list_document_chunks()
    if not chunks:
        raise ValueError("MySQL document_chunk 为空，无法构建 Qdrant 索引。")

    texts = [chunk.content.strip() or "empty" for chunk in chunks]
    embeddings = np.asarray(encode_texts(texts), dtype="float32")
    vector_size = int(embeddings.shape[1])
    average_document_length = (
        sum(chunk.token_count for chunk in chunks) / len(chunks)
    )
    client = get_qdrant_client()

    if client.collection_exists(QDRANT_COLLECTION_NAME):
        client.delete_collection(QDRANT_COLLECTION_NAME)
    client.create_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config={
            DENSE_VECTOR_NAME: models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            )
        },
    )
    client.create_payload_index(
        collection_name=QDRANT_COLLECTION_NAME,
        field_name="document_name",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )
    with Session(engine) as session:
        owner_map = {
            int(document.id): int(document.owner_id)
            for document in session.exec(select(DocumentRecord)).all()
            if document.id is not None and document.owner_id is not None
        }
    client.create_payload_index(
        collection_name=QDRANT_COLLECTION_NAME,
        field_name="document_id",
        field_schema=models.PayloadSchemaType.INTEGER,
        wait=True,
    )
    client.create_payload_index(
        collection_name=QDRANT_COLLECTION_NAME,
        field_name="owner_id",
        field_schema=models.PayloadSchemaType.INTEGER,
        wait=True,
    )

    for start in range(0, len(chunks), UPSERT_BATCH_SIZE):
        end = min(start + UPSERT_BATCH_SIZE, len(chunks))
        points = []
        for offset, chunk in enumerate(chunks[start:end], start=start):
            points.append(
                models.PointStruct(
                    id=int(chunk.id),
                    vector={
                        DENSE_VECTOR_NAME: embeddings[offset].tolist(),
                        SPARSE_VECTOR_NAME: encode_document_sparse(
                            chunk.content,
                            average_document_length,
                        ),
                    },
                    payload={
                        "document_chunk_id": int(chunk.id),
                        "document_id": chunk.document_id,
                        "owner_id": owner_map.get(int(chunk.document_id)),
                        "chunk_id": chunk.chunk_id,
                        "document_name": chunk.document_name,
                        "page_number": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                    },
                )
            )
        client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=points,
            wait=True,
        )

    _delete_orphan_points(
        client,
        expected_point_ids={int(chunk.id) for chunk in chunks},
    )

    _atomic_write_json(
        EMBEDDING_META_FILE,
        {
            "vector_store": "qdrant",
            "collection_name": QDRANT_COLLECTION_NAME,
            "retrieval": "dense+sparse+rrf",
            "dense_vector_name": DENSE_VECTOR_NAME,
            "sparse_vector_name": SPARSE_VECTOR_NAME,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "dim": vector_size,
            "chunk_count": len(chunks),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return len(chunks)


def upsert_qdrant_document_chunks(
    document_id: int,
    owner_id: int,
    document_chunks: list,
) -> int:
    """Replace one document's vectors without rebuilding other documents."""
    if not document_chunks:
        raise ValueError("该文档没有可写入 Qdrant 的切片。")

    client = get_qdrant_client()
    if not client.collection_exists(QDRANT_COLLECTION_NAME):
        build_qdrant_index_from_chunks()
        return len(document_chunks)

    all_chunks = list_document_chunks()
    average_document_length = (
        sum(chunk.token_count for chunk in all_chunks) / len(all_chunks)
    )
    texts = [chunk.content.strip() or "empty" for chunk in document_chunks]
    embeddings = np.asarray(encode_texts(texts), dtype="float32")

    points = []
    for offset, chunk in enumerate(document_chunks):
        points.append(
            models.PointStruct(
                id=int(chunk.id),
                vector={
                    DENSE_VECTOR_NAME: embeddings[offset].tolist(),
                    SPARSE_VECTOR_NAME: encode_document_sparse(
                        chunk.content,
                        average_document_length,
                    ),
                },
                payload={
                    "document_chunk_id": int(chunk.id),
                    "document_id": int(chunk.document_id),
                    "owner_id": int(owner_id),
                    "chunk_id": chunk.chunk_id,
                    "document_name": chunk.document_name,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                },
            )
        )

    client.delete(
        collection_name=QDRANT_COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=int(document_id)),
                    )
                ]
            )
        ),
        wait=True,
    )
    for start in range(0, len(points), UPSERT_BATCH_SIZE):
        client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=points[start : start + UPSERT_BATCH_SIZE],
            wait=True,
        )
    return len(points)


def delete_qdrant_document_chunks(document_id: int) -> None:
    """Remove vectors when the corresponding private document is deleted."""
    client = get_qdrant_client()
    if not client.collection_exists(QDRANT_COLLECTION_NAME):
        return
    client.delete(
        collection_name=QDRANT_COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=int(document_id)),
                    )
                ]
            )
        ),
        wait=True,
    )
