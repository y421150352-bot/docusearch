from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    document_name: str | None = None
