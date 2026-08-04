from pydantic import BaseModel, Field
#你希望模型输出成什么样”先定义清楚,给大模型输出结果用的结构定义,没有来源和编号

class KeyPointItem(BaseModel):
    #定义一个“关键点项”的结构
    title: str = Field(description="关键点标题")
    content: str = Field(description="关键点内容")
#Field也是 Pydantic 提供的。它的作用是：给字段加说明也可以加默认值、约束条件等在 FastAPI 文档里会显示出来对结构化输出也更友好

class QAResult(BaseModel):
    #整个问答结果的结构
    summary: str = Field(description="对问题的简洁总结")
    key_points: list[KeyPointItem] = Field(description="3条关键点列表")
     # list[KeyPointItem]表示key_points不是普通字符串，而是一个列表。而且这个列表里的每一项，都必须符合KeyPointItem这个结构。