from pathlib import Path

from app.config import CHUNK_SIZE, OVERLAP
from app.retrievers.indexer import parse_chunks_from_file
from app.retrievers.qdrant_indexer import upsert_qdrant_document_chunks
from app.services.document_chunk_service import (
    replace_document_chunks_for_document,
)
from app.services.document_service import (
    mark_document_index_failed,
    mark_document_ready,
)
from app.services.task_service import update_task_status


def run_document_ingestion_task(
    task_id: str,
    document_name: str,
    storage_path: str,
    owner_id: int,
) -> None:
    try:
        update_task_status(task_id, "running", "正在解析文档")
        path = Path(storage_path)
        chunks = parse_chunks_from_file(
            str(path),
            chunk_size=CHUNK_SIZE,
            overlap=OVERLAP,
        )
        # chunk_id was historically derived from the file name.  Prefix it so
        # two users may upload identically named files without a DB collision.
        for chunk in chunks:
            chunk["chunk_id"] = f"u{owner_id}__{chunk['chunk_id']}"

        update_task_status(task_id, "running", "正在批量写入 MySQL 切片")
        stored_chunks = replace_document_chunks_for_document(
            document_name,
            owner_id,
            chunks,
        )
        document_id = int(stored_chunks[0].document_id)

        update_task_status(task_id, "running", "正在生成并写入 Qdrant 向量")
        upsert_qdrant_document_chunks(document_id, owner_id, stored_chunks)

        mark_document_ready(document_name, owner_id)
        update_task_status(task_id, "completed", "文档已可用于问答")
    except Exception as exc:
        mark_document_index_failed(document_name, owner_id)
        update_task_status(task_id, "failed", f"文档处理失败: {exc}")
        raise
