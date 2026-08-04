from sqlmodel import SQLModel, Session, create_engine

from app.config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
)


def init_db() -> None:
    from app.models.chat_history_model import ChatHistoryRecord  # noqa: F401
    from app.models.document_chunk_model import DocumentChunk  # noqa: F401
    from app.models.document_model import DocumentRecord  # noqa: F401
    from app.models.feedback_model import FeedbackRecord  # noqa: F401
    from app.models.user_model import User
    from app.models.session_model import UserSession
    SQLModel.metadata.create_all(engine)
    from app.db.document_ownership_migration import apply_document_ownership_migration
    apply_document_ownership_migration()
    from app.db.chat_history_ownership_migration import apply_chat_history_ownership_migration
    apply_chat_history_ownership_migration()


def get_session():
    with Session(engine) as session:
        yield session
