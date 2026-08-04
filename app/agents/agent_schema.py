from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str
    document_name: str | None = None


class AgentChatResult(BaseModel):
    final_answer: str
    used_tools: list[str] = Field(default_factory=list)
    tool_result: dict = Field(default_factory=dict)
