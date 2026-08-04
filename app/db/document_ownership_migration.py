from sqlalchemy import inspect, text
from sqlmodel import Session, select

from app.db.database import engine
from app.models.document_model import DocumentRecord
from app.models.user_model import User


def apply_document_ownership_migration() -> None:
    """Add document ownership and assign legacy documents to root."""
    inspector = inspect(engine)
    if "documentrecord" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("documentrecord")}
    with engine.begin() as connection:
        if "owner_id" not in columns:
            connection.execute(
                text("ALTER TABLE documentrecord ADD COLUMN owner_id INTEGER NULL")
            )
            connection.execute(
                text("CREATE INDEX ix_documentrecord_owner_id ON documentrecord (owner_id)")
            )

        # MySQL does not support ``CREATE INDEX IF NOT EXISTS``.  Inspect the
        # table on every startup so this migration remains safe to run again.
        current_inspector = inspect(engine)
        indexes = current_inspector.get_indexes("documentrecord")
        unique_constraints = current_inspector.get_unique_constraints("documentrecord")
        all_indexes = indexes + unique_constraints
        for item in all_indexes:
            name = item.get("name")
            columns_for_index = item.get("column_names")
            if (
                name
                and name != "uq_documentrecord_owner_name"
                and columns_for_index == ["document_name"]
                and (item.get("unique") or item in unique_constraints)
            ):
                connection.execute(text(f"DROP INDEX `{name}` ON documentrecord"))

        # Re-inspect after dropping the old global uniqueness constraint.
        current_indexes = inspect(engine).get_indexes("documentrecord")
        current_constraints = inspect(engine).get_unique_constraints("documentrecord")
        has_owner_name_index = any(
            item.get("name") == "uq_documentrecord_owner_name"
            for item in current_indexes + current_constraints
        )
        if not has_owner_name_index:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_documentrecord_owner_name "
                    "ON documentrecord (owner_id, document_name)"
                )
            )

    with Session(engine) as session:
        root_user = session.exec(
            select(User).where(User.username == "root")
        ).first()
        if root_user is None or root_user.id is None:
            return
        legacy_documents = session.exec(
            select(DocumentRecord).where(DocumentRecord.owner_id.is_(None))
        ).all()
        for document in legacy_documents:
            document.owner_id = root_user.id
            session.add(document)
        session.commit()
