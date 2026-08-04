from sqlmodel import Session, select

from app.config import CHUNK_SIZE, OVERLAP
from app.db.database import engine
from app.models.document_model import DocumentRecord
from app.retrievers.indexer import parse_chunks_from_file
from app.retrievers.qdrant_indexer import upsert_qdrant_document_chunks
from app.services.document_chunk_service import replace_document_chunks_for_document
from app.services.document_service import (
    mark_document_index_failed,
    mark_document_ready,
)
from app.services.index_lock_service import (
    acquire_rebuild_index_lock,
    release_rebuild_index_lock,
)
from app.services.task_service import update_task_status


def run_rebuild_index_task(task_id: str, document_name: str | None = None) -> None:
    lock_acquired = False
    try:
        lock_acquired = acquire_rebuild_index_lock(task_id=task_id, ttl_seconds=600)
        if not lock_acquired:
            update_task_status(task_id, "rejected", "已有文档处理任务正在运行，请稍后重试")
            return

        # Reparse each stored document rather than scanning data/raw directly:
        # this preserves user ownership and removes newly classified noise such
        # as table-of-contents lines from both MySQL and Qdrant.
        with Session(engine) as session:
            documents = list(
                session.exec(
                    select(DocumentRecord).where(DocumentRecord.owner_id.is_not(None))
                ).all()
            )

        failed_names: list[str] = []
        for index, document in enumerate(documents, start=1):
            if document.id is None or document.owner_id is None:
                continue
            update_task_status(
                task_id,
                "running",
                f"正在重新解析 {index}/{len(documents)}：{document.document_name}",
            )
            try:
                chunks = parse_chunks_from_file(
                    document.storage_path,
                    chunk_size=CHUNK_SIZE,
                    overlap=OVERLAP,
                )
                for chunk in chunks:
                    chunk["chunk_id"] = f"u{document.owner_id}__{chunk['chunk_id']}"
                stored_chunks = replace_document_chunks_for_document(
                    document.document_name,
                    int(document.owner_id),
                    chunks,
                )
                upsert_qdrant_document_chunks(
                    int(document.id), int(document.owner_id), stored_chunks
                )
                mark_document_ready(document.document_name, int(document.owner_id))
            except Exception:
                failed_names.append(document.document_name)
                mark_document_index_failed(document.document_name, int(document.owner_id))

        if failed_names:
            update_task_status(
                task_id,
                "completed",
                f"已完成重建；{len(failed_names)} 个文档处理失败：{', '.join(failed_names[:3])}",
            )
        else:
            update_task_status(task_id, "completed", "已重新解析文献并更新 Qdrant 向量索引")
    except Exception as exc:
        update_task_status(task_id, "failed", f"文档处理失败: {exc}")
    finally:
        if lock_acquired:
            release_rebuild_index_lock(task_id)
