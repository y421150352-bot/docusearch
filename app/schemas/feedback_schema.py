from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    question: str
    answer: str
    document_name: str | None = None
    sources: list[dict] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)
    feedback_type: str
    feedback_reason: str | None = None
    feedback_comment: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    question: str
    answer: str
    document_name: str | None = None
    sources: list[dict] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)
    feedback_type: str
    feedback_reason: str | None = None
    feedback_comment: str | None = None
    created_at: datetime
