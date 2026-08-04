import json
from datetime import datetime

from sqlmodel import Session, select

from app.db.database import engine
from app.models.chat_history_model import ChatHistoryRecord
from app.schemas.response_schema import AnswerResponse


def _format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _record_to_dict(record: ChatHistoryRecord) -> dict:
    try:
        key_points = json.loads(record.key_points_json)
    except Exception:
        key_points = []

    try:
        sources = json.loads(record.sources_json)
    except Exception:
        sources = []

    return {
        "id": record.id,
        "question": record.question,
        "document_name": record.document_name,
        "summary": record.summary,
        "key_points": key_points,
        "sources": sources,
        "from_cache": record.from_cache,
        "latency_ms": record.latency_ms,
        "created_at": _format_datetime(record.created_at),
    }


def save_chat_history(
    question: str,
    response: AnswerResponse,
    owner_id: int,
    document_name: str | None = None,
    from_cache: bool = False,
    latency_ms: int = 0,
) -> dict:
    response_dict = response.model_dump()

    record = ChatHistoryRecord(
        owner_id=owner_id,
        question=question,
        document_name=document_name,
        summary=response.summary,
        key_points_json=json.dumps(response_dict.get("key_points", []), ensure_ascii=False),
        sources_json=json.dumps(response_dict.get("sources", []), ensure_ascii=False),
        from_cache=from_cache,
        latency_ms=latency_ms,
    )

    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return _record_to_dict(record)


def save_agent_chat_history(
    question: str,
    final_answer: str,
    owner_id: int,
    document_name: str | None = None,
    latency_ms: int = 0,
) -> dict:
    """Persist one complete /agent-chat turn regardless of the selected tool."""
    record = ChatHistoryRecord(
        owner_id=owner_id,
        question=question,
        document_name=document_name,
        summary=final_answer,
        key_points_json="[]",
        sources_json="[]",
        from_cache=False,
        latency_ms=latency_ms,
    )

    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return _record_to_dict(record)


def list_chat_history(owner_id: int, limit: int = 50) -> list[dict]:
    with Session(engine) as session:
        records = session.exec(
            select(ChatHistoryRecord)
            .where(ChatHistoryRecord.owner_id == owner_id)
            .order_by(ChatHistoryRecord.created_at.desc())
            .limit(limit)
        ).all()
        return [_record_to_dict(record) for record in records]


def delete_chat_history(history_id: int, owner_id: int) -> dict:
    with Session(engine) as session:
        record = session.exec(
            select(ChatHistoryRecord).where(
                ChatHistoryRecord.id == history_id,
                ChatHistoryRecord.owner_id == owner_id,
            )
        ).first()
        if not record:
            raise FileNotFoundError("chat history not found")
        session.delete(record)
        session.commit()
        return {"id": history_id}


def clear_chat_history(owner_id: int) -> dict:
    with Session(engine) as session:
        records = session.exec(
            select(ChatHistoryRecord).where(ChatHistoryRecord.owner_id == owner_id)
        ).all()
        count = len(records)
        for record in records:
            session.delete(record)
        session.commit()
        return {"deleted_count": count}
