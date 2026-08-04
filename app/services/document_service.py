from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlmodel import Session, delete, select

from app.config import RAW_DIR
from app.db.database import engine
from app.models.document_model import DocumentRecord
from app.models.document_chunk_model import DocumentChunk
from app.models.user_model import User
from app.retrievers.qdrant_indexer import delete_qdrant_document_chunks


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def _format_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _record_to_dict(record: DocumentRecord) -> dict:
    status = (record.index_status or "").strip().lower()
    if status == "indexed":
        status = "ready"
    elif status == "outdated":
        status = "processing"
    return {
        "id": record.id,
        "document_name": record.document_name,
        "file_type": record.file_type,
        "size_bytes": record.size_bytes,
        "storage_path": record.storage_path,
        "index_status": status,
        "index_version": record.index_version,
        "last_indexed_at": _format_datetime(record.last_indexed_at),
        "created_at": _format_datetime(record.created_at),
        "updated_at": _format_datetime(record.updated_at),
    }


def _validate_document_name(document_name: str) -> str:
    safe_name = Path(document_name).name
    if safe_name != document_name:
        raise ValueError("invalid document name")
    return safe_name


def _mark_processing(record: DocumentRecord) -> None:
    record.index_status = "processing"


def sync_documents_from_raw_dir() -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        existing_records = session.exec(select(DocumentRecord)).all()
        existing_map = {record.document_name: record for record in existing_records}
        current_file_names: set[str] = set()

        for path in RAW_DIR.iterdir():
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                continue

            current_file_names.add(path.name)
            stat = path.stat()
            updated_time = datetime.fromtimestamp(stat.st_mtime)
            existing = existing_map.get(path.name)

            if existing:
                modified_time_changed = (
                    abs((existing.updated_at - updated_time).total_seconds()) > 1
                )
                metadata_changed = (
                    existing.file_type != suffix.lstrip(".")
                    or existing.size_bytes != stat.st_size
                    or modified_time_changed
                )
                existing.file_type = suffix.lstrip(".")
                existing.size_bytes = stat.st_size
                existing.storage_path = str(path)
                existing.updated_at = updated_time
                if metadata_changed:
                    _mark_processing(existing)
                session.add(existing)
                continue

            session.add(
                DocumentRecord(
                    document_name=path.name,
                    file_type=suffix.lstrip("."),
                    size_bytes=stat.st_size,
                    storage_path=str(path),
                    index_status="processing",
                    index_version=0,
                    last_indexed_at=None,
                    created_at=updated_time,
                    updated_at=updated_time,
                )
            )

        for record in existing_records:
            if record.document_name not in current_file_names:
                session.exec(
                    delete(DocumentChunk).where(
                        DocumentChunk.document_id == record.id
                    )
                )
                session.delete(record)

        session.commit()

        records = session.exec(
            select(DocumentRecord).order_by(DocumentRecord.updated_at.desc())
        ).all()
        return [_record_to_dict(record) for record in records]


def list_documents(owner_id: int) -> list[dict]:
    with Session(engine) as session:
        records = session.exec(
            select(DocumentRecord)
            .where(DocumentRecord.owner_id == owner_id)
            .order_by(DocumentRecord.updated_at.desc())
        ).all()
        return [_record_to_dict(record) for record in records]


def list_all_documents() -> list[dict]:
    """Admin-only document list, annotated with its owning account."""
    with Session(engine) as session:
        rows = session.exec(
            select(DocumentRecord, User)
            .join(User, DocumentRecord.owner_id == User.id, isouter=True)
            .order_by(DocumentRecord.updated_at.desc())
        ).all()
        return [
            {
                **_record_to_dict(document),
                "owner_id": document.owner_id,
                "owner_username": user.username if user else "未知用户",
            }
            for document, user in rows
        ]


def get_document_detail(document_name: str, owner_id: int) -> dict | None:
    safe_name = _validate_document_name(document_name)
    with Session(engine) as session:
        record = session.exec(
            select(DocumentRecord).where(
                DocumentRecord.document_name == safe_name,
                DocumentRecord.owner_id == owner_id,
            )
        ).first()
        if record is None:
            return None
        return _record_to_dict(record)


def get_document_index_stats(owner_id: int | None = None) -> dict:
    with Session(engine) as session:
        statement = select(DocumentRecord)
        if owner_id is not None:
            statement = statement.where(DocumentRecord.owner_id == owner_id)
        records = session.exec(statement).all()
        total = len(records)
        status_counts = {"ready": 0, "processing": 0, "failed": 0}
        status_documents = {"ready": [], "processing": [], "failed": []}
        for record in records:
            status = (record.index_status or "").strip().lower()
            if status == "indexed":
                status = "ready"
            elif status == "outdated":
                status = "processing"
            if status in status_counts:
                status_counts[status] += 1
                status_documents[status].append(record.document_name)

        return {
            "document_count": total,
            "ready_count": status_counts["ready"],
            "processing_count": status_counts["processing"],
            "failed_count": status_counts["failed"],
            "ready_documents": status_documents["ready"],
            "processing_documents": status_documents["processing"],
            "failed_documents": status_documents["failed"],
            # Keep the old keys while agent tools migrate to the new wording.
            "indexed_count": status_counts["ready"],
            "outdated_count": status_counts["processing"],
            "indexed_documents": status_documents["ready"],
            "outdated_documents": status_documents["processing"],
        }


async def save_uploaded_document(file: UploadFile, owner_id: int) -> dict:
    owner_dir = RAW_DIR / str(owner_id)
    owner_dir.mkdir(parents=True, exist_ok=True)

    filename = (file.filename or "").strip()
    if not filename:
        raise ValueError("empty filename")

    safe_name = _validate_document_name(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("only pdf txt md are supported")

    content = await file.read()
    if not content:
        raise ValueError("empty file content")

    target_path = owner_dir / safe_name
    with open(target_path, "wb") as file_object:
        file_object.write(content)

    stat = target_path.stat()
    now = datetime.fromtimestamp(stat.st_mtime)

    with Session(engine) as session:
        existing = session.exec(
            select(DocumentRecord).where(
                DocumentRecord.document_name == target_path.name,
                DocumentRecord.owner_id == owner_id,
            )
        ).first()

        if existing:
            existing.file_type = suffix.lstrip(".")
            existing.size_bytes = stat.st_size
            existing.storage_path = str(target_path)
            existing.updated_at = now
            _mark_processing(existing)
            record = existing
        else:
            record = DocumentRecord(
                document_name=target_path.name,
                owner_id=owner_id,
                file_type=suffix.lstrip("."),
                size_bytes=stat.st_size,
                storage_path=str(target_path),
                index_status="processing",
                index_version=0,
                last_indexed_at=None,
                created_at=now,
                updated_at=now,
            )

        session.add(record)
        session.commit()
        session.refresh(record)
        return _record_to_dict(record)


def delete_document(document_name: str, owner_id: int) -> dict:
    safe_name = _validate_document_name(document_name)
    with Session(engine) as session:
        record = session.exec(
            select(DocumentRecord).where(
                DocumentRecord.document_name == safe_name,
                DocumentRecord.owner_id == owner_id,
            )
        ).first()
        if record is None:
            raise FileNotFoundError("document not found")
        document_id = int(record.id)
        target_path = Path(record.storage_path)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
        # Remove the vector copy before deleting its relational source rows.
        delete_qdrant_document_chunks(document_id)
        session.exec(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        session.delete(record)
        session.commit()

    return {"document_name": safe_name}


def delete_document_by_id(document_id: int) -> dict:
    """Admin maintenance deletion for any user's document."""
    with Session(engine) as session:
        record = session.get(DocumentRecord, document_id)
        if record is None:
            raise FileNotFoundError("document not found")
        target_path = Path(record.storage_path)
        delete_qdrant_document_chunks(int(record.id))
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
        session.exec(
            delete(DocumentChunk).where(DocumentChunk.document_id == int(record.id))
        )
        document_name = record.document_name
        session.delete(record)
        session.commit()
    return {"id": document_id, "document_name": document_name}


def mark_all_documents_ready() -> None:
    now = datetime.utcnow()
    with Session(engine) as session:
        records = session.exec(select(DocumentRecord)).all()
        for record in records:
            record.index_status = "ready"
            record.index_version += 1
            record.last_indexed_at = now
            session.add(record)
        session.commit()


def mark_all_documents_processing() -> None:
    with Session(engine) as session:
        records = session.exec(select(DocumentRecord)).all()
        for record in records:
            record.index_status = "processing"
            session.add(record)
        session.commit()


def mark_document_index_failed(document_name: str, owner_id: int) -> None:
    safe_name = _validate_document_name(document_name)
    with Session(engine) as session:
        record = session.exec(
            select(DocumentRecord).where(
                DocumentRecord.document_name == safe_name,
                DocumentRecord.owner_id == owner_id,
            )
        ).first()
        if record:
            record.index_status = "failed"
            session.add(record)
            session.commit()


def mark_document_ready(document_name: str, owner_id: int) -> None:
    safe_name = _validate_document_name(document_name)
    now = datetime.utcnow()
    with Session(engine) as session:
        record = session.exec(
            select(DocumentRecord).where(
                DocumentRecord.document_name == safe_name,
                DocumentRecord.owner_id == owner_id,
            )
        ).first()
        if record:
            record.index_status = "ready"
            record.index_version += 1
            record.last_indexed_at = now
            session.add(record)
            session.commit()


def mark_all_documents_index_failed() -> None:
    with Session(engine) as session:
        records = session.exec(select(DocumentRecord)).all()
        for record in records:
            record.index_status = "failed"
            session.add(record)
        session.commit()
