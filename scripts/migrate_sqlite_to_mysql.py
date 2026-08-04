"""One-time migration of legacy data/app.db records to configured MySQL."""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import engine, init_db
from app.models.chat_history_model import ChatHistoryRecord
from app.models.document_model import DocumentRecord
from app.models.feedback_model import FeedbackRecord


SQLITE_PATH = PROJECT_ROOT / "data" / "app.db"


def _datetime(value):
    if not value or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _copy_table(
    source: sqlite3.Connection,
    session: Session,
    table_name: str,
    model,
    datetime_fields: tuple[str, ...],
) -> int:
    table_exists = source.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    if not table_exists:
        return 0

    copied = 0
    rows = source.execute(f"SELECT * FROM {table_name}").fetchall()
    for row in rows:
        payload = dict(row)
        for field_name in datetime_fields:
            if field_name in payload:
                payload[field_name] = _datetime(payload[field_name])
        record_id = payload.get("id")
        if record_id is not None and session.exec(
            select(model).where(model.id == record_id)
        ).first():
            continue
        session.add(model(**payload))
        copied += 1
    session.commit()
    return copied


def main() -> None:
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"legacy SQLite database not found: {SQLITE_PATH}")

    init_db()
    source = sqlite3.connect(SQLITE_PATH)
    source.row_factory = sqlite3.Row
    try:
        with Session(engine) as session:
            counts = {
                "documentrecord": _copy_table(
                    source,
                    session,
                    "documentrecord",
                    DocumentRecord,
                    ("last_indexed_at", "created_at", "updated_at"),
                ),
                "chathistoryrecord": _copy_table(
                    source,
                    session,
                    "chathistoryrecord",
                    ChatHistoryRecord,
                    ("created_at",),
                ),
                "feedbackrecord": _copy_table(
                    source,
                    session,
                    "feedbackrecord",
                    FeedbackRecord,
                    ("created_at",),
                ),
            }
    finally:
        source.close()

    print(f"migration completed: {counts}")


if __name__ == "__main__":
    main()
