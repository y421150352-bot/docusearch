#创建一个基于 LangChain 的大模型客户端，并要求它按你定义好的结构化格式输出结果。
from langchain_deepseek import ChatDeepSeek#创建一个 LangChain 版的 DeepSeek 聊天模型对象
from app.config import LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT
from app.schemas.llm_schema import QAResult

#给项目提供统一的大模型对象入口
def get_langchain_llm():
    llm = ChatDeepSeek(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        timeout=LLM_TIMEOUT,
        temperature=0.2,
        #如果请求失败，最多自动重试 2 次
        max_retries=2,
    )
    return llm.with_structured_output(QAResult)
#尽量让模型输出贴近 QAResult 这个结构