from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class DocumentRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(
        default=None,
        foreign_key="user.id",
        index=True,
    )
    document_name: str = Field(index=True)
    file_type: str
    size_bytes: int
    storage_path: str
    index_status: str = Field(default="processing")
    index_version: int = Field(default=0)
    last_indexed_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
