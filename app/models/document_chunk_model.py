from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunk"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="documentrecord.id", index=True)
    chunk_id: str = Field(index=True, unique=True, max_length=255)
    document_name: str = Field(index=True, max_length=255)
    page_number: int = Field(default=1)
    chunk_index: int = Field(default=0)
    content: str = Field(sa_column=Column(Text, nullable=False))
    content_hash: str = Field(max_length=64, index=True)
    token_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
