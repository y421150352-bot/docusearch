from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agents.agent_tools import get_agent_tools, reset_agent_owner, set_agent_owner
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT


SYSTEM_PROMPT = (
    "\u4f60\u662f DocuSearch Agent\uff0c\u4e00\u4e2a\u9762\u5411\u7814\u7a76\u751f\u3001\u8bba\u6587\u9605\u8bfb\u8005\u548c\u79d1\u7814\u4eba\u5458\u7684\u79c1\u6709\u77e5\u8bc6\u5e93\u5b66\u672f\u52a9\u624b\u3002\n"
    "\u4f60\u7684\u56de\u7b54\u8981\u6df1\u5165\u3001\u7cfb\u7edf\u3001\u7ed3\u6784\u6e05\u6670\uff0c\u9002\u5408\u7528\u4e8e\u8bba\u6587\u9605\u8bfb\u3001\u8bfe\u9898\u5b66\u4e60\u3001\u5b9e\u9a8c\u8bbe\u8ba1\u548c\u7814\u7a76\u7efc\u8ff0\u3002\n"
    "\u4f60\u4e0d\u8981\u53ea\u505a\u7b80\u5355\u6982\u62ec\uff0c\u4e5f\u4e0d\u8981\u673a\u68b0\u5730\u8bf4\u201c\u591a\u7bc7\u6587\u6863\u5171\u540c\u8868\u660e\u201d\u3002\n"
    "\u5982\u679c\u95ee\u9898\u662f\u201c\u600e\u4e48\u505a/\u600e\u4e48\u6784\u5efa/\u5982\u4f55\u5efa\u7acb/\u5982\u4f55\u5b9e\u73b0\u201d\uff0c\u4f60\u8981\u5c3d\u91cf\u6309\u7167\uff1a\u6982\u5ff5\u4e0e\u76ee\u6807\u3001\u7406\u8bba\u4f9d\u636e\u3001\u6570\u636e\u6765\u6e90\u3001\u91c7\u96c6\u4e0e\u9884\u5904\u7406\u3001\u7279\u5f81\u6784\u5efa\u3001\u6807\u7b7e\u6784\u5efa\u3001\u6a21\u578b\u5efa\u7acb\u3001\u8bc4\u4ef7\u6307\u6807\u3001\u5e94\u7528\u4e0e\u5c40\u9650\u7684\u7ed3\u6784\u7ec4\u7ec7\u56de\u7b54\u3002\n"
    "\u5982\u679c\u6587\u6863\u8bc1\u636e\u4e0d\u8db3\uff0c\u8981\u660e\u786e\u8bf4\u201c\u6587\u6863\u4e2d\u672a\u5145\u5206\u8bf4\u660e\u201d\uff0c\u5e76\u5728\u5fc5\u8981\u65f6\u6807\u6ce8\u201c\u4ee5\u4e0b\u5185\u5bb9\u5c5e\u4e8e\u57fa\u4e8e\u73b0\u6709\u6750\u6599\u7684\u5f52\u7eb3\u63a8\u5bfc\u201d\u3002\n\n"
    "\u4f60\u53ef\u4ee5\u4f7f\u7528\u5de5\u5177\u5b8c\u6210\uff1a\n"
    "1. \u56de\u7b54\u77e5\u8bc6\u5e93\u6587\u6863\u76f8\u5173\u95ee\u9898\n"
    "2. \u67e5\u770b\u77e5\u8bc6\u5e93\u6587\u6863\u5217\u8868\u4e0e\u8be6\u60c5\n"
    "3. \u68c0\u67e5\u7d22\u5f15\u5065\u5eb7\u72b6\u6001\n"
    "4. \u53ea\u68c0\u7d22\u539f\u6587\u7247\u6bb5\u548c\u6765\u6e90\n"
    "5. \u603b\u7ed3\u5355\u7bc7\u6587\u6863\u6216\u6bd4\u8f83\u4e24\u7bc7\u6587\u6863\n"
    "6. \u67e5\u770b\u95ee\u7b54\u5386\u53f2\n"
    "7. \u67e5\u8be2\u7d22\u5f15\u91cd\u5efa\u4efb\u52a1\u72b6\u6001\n\n"
    "\u5de5\u5177\u9009\u62e9\u89c4\u5219\uff1a\n"
    "- \u5982\u679c\u7528\u6237\u95ee\u67d0\u4e2a\u6587\u6863\u662f\u5426\u5df2\u7d22\u5f15\u3001\u6587\u6863\u8be6\u60c5\u3001\u4e0a\u4f20\u65f6\u95f4\u3001\u7d22\u5f15\u7248\u672c\uff0c\u8bf7\u8c03\u7528 document_detail_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u95ee\u77e5\u8bc6\u5e93\u662f\u5426\u6b63\u5e38\u3001\u54ea\u4e9b\u6587\u6863\u9700\u8981\u91cd\u5efa\u7d22\u5f15\u3001\u5f53\u524d\u7d22\u5f15\u72b6\u6001\uff0c\u8bf7\u8c03\u7528 index_health_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u8bf4\u53ea\u60f3\u627e\u539f\u6587\u3001\u627e\u6765\u6e90\u3001\u627e\u76f8\u5173\u7247\u6bb5\u3001\u4e0d\u8981\u603b\u7ed3\uff0c\u8bf7\u8c03\u7528 search_sources_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u8bf4\u603b\u7ed3\u67d0\u7bc7\u6587\u6863\uff0c\u8bf7\u8c03\u7528 summarize_document_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u8bf4\u6bd4\u8f83\u4e24\u7bc7\u6587\u6863\uff0c\u8bf7\u8c03\u7528 compare_documents_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u95ee\u6587\u6863\u5185\u5bb9\u3001\u6587\u7ae0\u7814\u7a76\u5185\u5bb9\u3001\u77e5\u8bc6\u5e93\u603b\u7ed3\uff0c\u8bf7\u8c03\u7528 rag_qa_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u95ee\u6709\u54ea\u4e9b\u6587\u6863\u3001\u6587\u4ef6\u5217\u8868\u3001\u77e5\u8bc6\u5e93\u91cc\u6709\u4ec0\u4e48\uff0c\u8bf7\u8c03\u7528 list_documents_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u95ee\u6700\u8fd1\u95ee\u8fc7\u4ec0\u4e48\u3001\u5386\u53f2\u8bb0\u5f55\uff0c\u8bf7\u8c03\u7528 chat_history_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u63d0\u4f9b task_id \u5e76\u8be2\u95ee\u4efb\u52a1\u72b6\u6001\uff0c\u8bf7\u8c03\u7528 task_status_tool\u3002\n"
    "- \u5982\u679c\u7528\u6237\u8981\u6c42\u91cd\u5efa\u7d22\u5f15\uff0c\u4f60\u4e0d\u80fd\u76f4\u63a5\u8c03\u7528\u5de5\u5177\uff0c\u56e0\u4e3a\u8fd9\u662f\u6709\u526f\u4f5c\u7528\u64cd\u4f5c\uff0c\u8bf7\u63d0\u793a\u7528\u6237\u8f93\u5165\u201c\u786e\u8ba4\u91cd\u5efa\u7d22\u5f15\u201d\u3002\n"
    "- \u5982\u679c\u7528\u6237\u8981\u6c42\u6e05\u7406\u7f13\u5b58\uff0c\u4f60\u4e0d\u80fd\u76f4\u63a5\u6267\u884c\uff0c\u8bf7\u63d0\u793a\u7528\u6237\u8f93\u5165\u201c\u786e\u8ba4\u6e05\u7406\u7f13\u5b58\u201d\u3002\n"
    "- \u4f60\u5fc5\u987b\u6839\u636e\u5de5\u5177\u8fd4\u56de\u7ed3\u679c\u7ec4\u7ec7\u4e2d\u6587\u56de\u7b54\u3002\n"
    "- \u4e0d\u8981\u7f16\u9020\u5de5\u5177\u6ca1\u6709\u8fd4\u56de\u7684\u4fe1\u606f\u3002\n"
    "- 使用严谨、克制的学术写作风格，禁止使用 emoji、颜文字或装饰性图标。\n"
    "- 不要用图标代替标题或项目符号；使用标准 Markdown 标题、段落、编号、列表和表格。\n"
    "- 数学公式必须使用标准 LaTeX：行内公式写作 $...$，独立公式写作 $$...$$；不要使用 Unicode 字符拼凑公式。\n"
    "- 除非用户明确要求，避免重复调用参数相同的同一个工具。工具已返回充分结果时应直接组织最终回答。"
)


def _normalize_openai_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def create_docusearch_agent(owner_id: int):
    llm = ChatOpenAI(
        api_key=LLM_API_KEY,
        base_url=_normalize_openai_base_url(LLM_BASE_URL),
        model=LLM_MODEL,
        temperature=0.1,
        timeout=LLM_TIMEOUT,
        max_retries=2,
    )
    return create_agent(
        model=llm,
        tools=get_agent_tools(),
        system_prompt=SYSTEM_PROMPT,
        name="docusearch_agent",
    )


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            elif isinstance(item, str) and item.strip():
                parts.append(item.strip())
        return "\n".join(parts).strip()
    return str(content or "").strip()


def _extract_used_tools(agent_result) -> list[str]:
    try:
        messages = agent_result.get("messages", [])
        used_tools: list[str] = []
        for message in messages:
            if isinstance(message, AIMessage):
                for tool_call in getattr(message, "tool_calls", []) or []:
                    tool_name = tool_call.get("name")
                    if isinstance(tool_name, str) and tool_name not in used_tools:
                        used_tools.append(tool_name)
        return used_tools
    except Exception:
        return []


def _extract_final_answer(agent_result) -> str:
    messages = agent_result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = _message_text(message.content)
            if content:
                return content
    return "\u672a\u83b7\u53d6\u5230\u6709\u6548\u56de\u7b54\u3002"


def _extract_tool_results(agent_result) -> dict:
    try:
        messages = agent_result.get("messages", [])
        tool_results: dict[str, object] = {}
        for message in messages:
            if isinstance(message, ToolMessage):
                tool_name = getattr(message, "name", None) or "unknown_tool"
                content = _message_text(message.content)
                tool_results[tool_name] = content
        return tool_results
    except Exception:
        return {}


def run_langchain_agent(
    message: str,
    document_name: str | None = None,
    owner_id: int = 0,
) -> dict:
    context_token = None
    try:
        context_token = set_agent_owner(owner_id)
        agent = create_docusearch_agent(owner_id)
        user_message = message
        if document_name:
            user_message = (
                f"{message}\n\n"
                f"\u7528\u6237\u5f53\u524d\u9009\u62e9\u7684\u6587\u6863\u662f\uff1a{document_name}\u3002"
                f"\u5982\u679c\u9700\u8981\u56de\u7b54\u6587\u6863\u5185\u5bb9\u95ee\u9898\uff0c"
                f"\u8bf7\u5c06 document_name \u53c2\u6570\u8bbe\u7f6e\u4e3a\uff1a{document_name}\u3002"
            )

        agent_result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ]
            }
        )

        result = {
            "success": True,
            "final_answer": _extract_final_answer(agent_result),
            "used_tools": _extract_used_tools(agent_result),
            "tool_result": _extract_tool_results(agent_result),
        }
        return result
    except Exception as exc:
        return {
            "success": False,
            "final_answer": f"Agent 调用失败：{exc}",
            "used_tools": [],
            "tool_result": {
                "success": False,
                "error": str(exc),
            },
        }
    finally:
        if context_token is not None:
            reset_agent_owner(context_token)
