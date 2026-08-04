from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class ChatHistoryRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    question: str = Field(sa_column=Column(Text, nullable=False))
    document_name: Optional[str] = Field(default=None, nullable=True)
    summary: str = Field(sa_column=Column(Text, nullable=False))
    key_points_json: str = Field(sa_column=Column(Text, nullable=False))
    sources_json: str = Field(sa_column=Column(Text, nullable=False))
    from_cache: bool = False
    latency_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
