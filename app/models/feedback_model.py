from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class FeedbackRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    question: str = Field(sa_column=Column(Text, nullable=False))
    answer: str = Field(sa_column=Column(Text, nullable=False))
    document_name: Optional[str] = Field(default=None, nullable=True)
    sources_json: str = Field(sa_column=Column(Text, nullable=False))
    used_tools_json: str = Field(sa_column=Column(Text, nullable=False))
    feedback_type: str
    feedback_reason: Optional[str] = Field(default=None, nullable=True)
    feedback_comment: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
