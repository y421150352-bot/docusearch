import json

from sqlmodel import Session, select

from app.db.database import engine
from app.models.feedback_model import FeedbackRecord
from app.schemas.feedback_schema import FeedbackCreateRequest


def _record_to_dict(record: FeedbackRecord) -> dict:
    try:
        sources = json.loads(record.sources_json)
    except Exception:
        sources = []

    try:
        used_tools = json.loads(record.used_tools_json)
    except Exception:
        used_tools = []

    return {
        "id": record.id,
        "question": record.question,
        "answer": record.answer,
        "document_name": record.document_name,
        "sources": sources,
        "used_tools": used_tools,
        "feedback_type": record.feedback_type,
        "feedback_reason": record.feedback_reason,
        "feedback_comment": record.feedback_comment,
        "created_at": record.created_at,
    }


def create_feedback(request: FeedbackCreateRequest) -> dict:
    record = FeedbackRecord(
        question=request.question,
        answer=request.answer,
        document_name=request.document_name,
        sources_json=json.dumps(request.sources, ensure_ascii=False),
        used_tools_json=json.dumps(request.used_tools, ensure_ascii=False),
        feedback_type=request.feedback_type,
        feedback_reason=request.feedback_reason,
        feedback_comment=request.feedback_comment,
    )
    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return _record_to_dict(record)


def list_feedback(limit: int = 100) -> list[dict]:
    with Session(engine) as session:
        records = session.exec(
            select(FeedbackRecord)
            .order_by(FeedbackRecord.created_at.desc())
            .limit(limit)
        ).all()
        return [_record_to_dict(record) for record in records]


def delete_feedback(feedback_id: int) -> dict:
    with Session(engine) as session:
        record = session.get(FeedbackRecord, feedback_id)
        if not record:
            raise FileNotFoundError("feedback not found")
        session.delete(record)
        session.commit()
        return {"id": feedback_id}
