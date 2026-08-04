import hashlib
from pathlib import Path

from sqlmodel import Session, delete, func, select

from app.db.database import engine
from app.models.document_chunk_model import DocumentChunk
from app.models.document_model import DocumentRecord
from app.retrievers.sparse_encoder import tokenize_for_sparse


def _parse_chunk_index(chunk_id: str) -> int:
    try:
        return int(chunk_id.rsplit("_c", 1)[1])
    except (IndexError, ValueError):
        return 0


def replace_document_chunks(chunks: list[dict]) -> int:
    """Atomically replace the relational chunk snapshot used by Qdrant."""
    if not chunks:
        raise ValueError("没有可写入 MySQL 的文档片段。")

    with Session(engine) as session:
        documents = session.exec(select(DocumentRecord)).all()
        document_map = {item.document_name: item for item in documents}

        for chunk in chunks:
            name = str(chunk["document_name"])
            if name in document_map:
                continue
            path = Path(name)
            record = DocumentRecord(
                document_name=name,
                file_type=path.suffix.lstrip(".") or "txt",
                size_bytes=0,
                storage_path=str(path),
            )
            session.add(record)
            session.flush()
            document_map[name] = record

        session.exec(delete(DocumentChunk))
        for chunk in chunks:
            content = str(chunk.get("content", "")).strip()
            name = str(chunk["document_name"])
            record = document_map[name]
            session.add(
                DocumentChunk(
                    document_id=int(record.id),
                    chunk_id=str(chunk["chunk_id"]),
                    document_name=name,
                    page_number=int(chunk.get("page_number") or 1),
                    chunk_index=_parse_chunk_index(str(chunk["chunk_id"])),
                    content=content,
                    content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    token_count=len(tokenize_for_sparse(content)),
                )
            )
        session.commit()
    return len(chunks)


def replace_document_chunks_for_document(
    document_name: str,
    owner_id: int,
    chunks: list[dict],
) -> list[DocumentChunk]:
    """Atomically replace only one document's relational chunks."""
    if not chunks:
        raise ValueError("该文档没有可写入 MySQL 的文本片段。")
    if any(str(chunk["document_name"]) != document_name for chunk in chunks):
        raise ValueError("文档切片中包含了其他文档。")

    with Session(engine) as session:
        document = session.exec(
            select(DocumentRecord).where(
                DocumentRecord.document_name == document_name,
                DocumentRecord.owner_id == owner_id,
            )
        ).first()
        if document is None or document.id is None:
            raise FileNotFoundError("文档记录不存在。")

        session.exec(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == int(document.id)
            )
        )
        for chunk in chunks:
            content = str(chunk.get("content", "")).strip()
            session.add(
                DocumentChunk(
                    document_id=int(document.id),
                    chunk_id=str(chunk["chunk_id"]),
                    document_name=document_name,
                    page_number=int(chunk.get("page_number") or 1),
                    chunk_index=_parse_chunk_index(str(chunk["chunk_id"])),
                    content=content,
                    content_hash=hashlib.sha256(
                        content.encode("utf-8")
                    ).hexdigest(),
                    token_count=len(tokenize_for_sparse(content)),
                )
            )
        session.commit()
        rows = session.exec(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == int(document.id))
            .order_by(DocumentChunk.id)
        ).all()
        return list(rows)


def list_document_chunks() -> list[DocumentChunk]:
    with Session(engine) as session:
        return list(
            session.exec(
                select(DocumentChunk).order_by(DocumentChunk.id)
            ).all()
        )


def get_document_chunks_by_ids(chunk_ids: list[int]) -> dict[int, DocumentChunk]:
    if not chunk_ids:
        return {}
    with Session(engine) as session:
        rows = session.exec(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        ).all()
        return {int(row.id): row for row in rows}


def count_document_chunks(owner_id: int | None = None) -> int:
    with Session(engine) as session:
        statement = select(func.count()).select_from(DocumentChunk)
        if owner_id is not None:
            statement = statement.join(DocumentRecord).where(
                DocumentRecord.owner_id == owner_id
            )
        return int(session.exec(statement).one())
