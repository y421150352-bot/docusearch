from pydantic import BaseModel
from typing import List
# Pydantic 是 FastAPI 推荐的一个库，它用来定义数据结构并进行数据验证。
# BaseModel 是 Pydantic 提供的一个基类，所有的数据结构类（比如 AnswerResponse）都继承自它
#API 接口最终响应结构
class KeyPoint(BaseModel):
    title: str
    content: str

class SourceItem(BaseModel):
    document_name: str
    page_number: int
    quote: str
    score: float | None = None
    rerank_score: float | None = None
    retrieval_type: str | None = None

class AnswerResponse(BaseModel):
    question: str
    summary: str
    key_points: List[KeyPoint]
    sources: List[SourceItem]
