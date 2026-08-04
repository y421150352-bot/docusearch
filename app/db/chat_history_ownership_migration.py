from sqlalchemy import inspect, text
from sqlmodel import Session, select

from app.db.database import engine
from app.models.chat_history_model import ChatHistoryRecord
from app.models.user_model import User


def apply_chat_history_ownership_migration() -> None:
    """Add ownership to existing conversation history without losing records."""
    inspector = inspect(engine)
    if "chathistoryrecord" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("chathistoryrecord")}
    with engine.begin() as connection:
        if "owner_id" not in columns:
            connection.execute(
                text("ALTER TABLE chathistoryrecord ADD COLUMN owner_id INTEGER NULL")
            )
            connection.execute(
                text("CREATE INDEX ix_chathistoryrecord_owner_id ON chathistoryrecord (owner_id)")
            )

    with Session(engine) as session:
        root_user = session.exec(select(User).where(User.username == "root")).first()
        if root_user is None or root_user.id is None:
            return
        for record in session.exec(
            select(ChatHistoryRecord).where(ChatHistoryRecord.owner_id.is_(None))
        ).all():
            record.owner_id = root_user.id
            session.add(record)
        session.commit()
