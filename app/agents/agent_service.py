from fastapi import BackgroundTasks
import time

from app.agents.agent_schema import AgentChatRequest, AgentChatResult
from app.agents.langchain_agent import run_langchain_agent
from app.services.cache_service import clear_qa_cache
from app.services.index_task_service import run_rebuild_index_task
from app.services.history_service import save_agent_chat_history
from app.services.task_service import create_task_id, create_task_record


REBUILD_CONFIRM_KEYWORDS = (
    "\u786e\u8ba4\u91cd\u5efa\u7d22\u5f15",
    "\u786e\u8ba4\u6267\u884c\u91cd\u5efa\u7d22\u5f15",
    "\u786e\u8ba4\u66f4\u65b0\u7d22\u5f15",
    "confirm rebuild index",
)

REBUILD_REQUEST_KEYWORDS = (
    "\u91cd\u5efa\u7d22\u5f15",
    "\u91cd\u65b0\u7d22\u5f15",
    "\u66f4\u65b0\u7d22\u5f15",
    "\u66f4\u65b0\u77e5\u8bc6\u5e93",
    "\u91cd\u65b0\u6784\u5efa\u7d22\u5f15",
)

CLEAR_CACHE_CONFIRM_KEYWORDS = (
    "\u786e\u8ba4\u6e05\u7406\u7f13\u5b58",
    "confirm clear cache",
)

CLEAR_CACHE_REQUEST_KEYWORDS = (
    "\u6e05\u7406\u7f13\u5b58",
    "\u6e05\u7a7a\u7f13\u5b58",
    "\u5237\u65b0\u7f13\u5b58",
)

CONFIRMATION_PROMPT = (
    "\u91cd\u5efa\u7d22\u5f15\u4f1a\u91cd\u65b0\u5904\u7406\u77e5\u8bc6\u5e93\u6587\u6863\u5e76\u66f4\u65b0\u68c0\u7d22\u7d22\u5f15\u3002"
    "\u5982\u679c\u786e\u8ba4\u6267\u884c\uff0c\u8bf7\u8f93\u5165\uff1a\u786e\u8ba4\u91cd\u5efa\u7d22\u5f15\u3002"
)

CLEAR_CACHE_CONFIRMATION_PROMPT = "清理缓存只会删除 qa_cache: 开头的问答缓存。如需继续，请输入：确认清理缓存。"


def _contains_keyword(message: str, keywords: tuple[str, ...]) -> bool:
    normalized = message.strip().lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _run_agent_chat_impl(
    request: AgentChatRequest,
    background_tasks: BackgroundTasks,
    owner_id: int,
) -> AgentChatResult:
    message = request.message.strip()

    if _contains_keyword(message, REBUILD_CONFIRM_KEYWORDS):
        task_id = create_task_id()
        create_task_record(task_id=task_id, task_type="rebuild_index")
        background_tasks.add_task(run_rebuild_index_task, task_id)
        return AgentChatResult(
            final_answer=f"\u5df2\u786e\u8ba4\u6267\u884c\u7d22\u5f15\u91cd\u5efa\uff0c\u4efb\u52a1 ID\uff1a{task_id}",
            used_tools=["rebuild_index_task"],
            tool_result={
                "task_id": task_id,
                "task_type": "rebuild_index",
                "status": "pending",
            },
        )

    if _contains_keyword(message, CLEAR_CACHE_CONFIRM_KEYWORDS):
        try:
            clear_result = clear_qa_cache()
            return AgentChatResult(
                final_answer=f"已清理问答缓存，删除 {clear_result['deleted_count']} 个缓存键。",
                used_tools=["clear_cache_task"],
                tool_result=clear_result,
            )
        except Exception as exc:
            return AgentChatResult(
                final_answer=f"清理缓存失败：{exc}",
                used_tools=["clear_cache_task"],
                tool_result={
                    "success": False,
                    "error": str(exc),
                },
            )

    if _contains_keyword(message, REBUILD_REQUEST_KEYWORDS):
        return AgentChatResult(
            final_answer=CONFIRMATION_PROMPT,
            tool_result={
                "requires_confirmation": True,
                "operation": "rebuild_index",
            },
        )

    if _contains_keyword(message, CLEAR_CACHE_REQUEST_KEYWORDS):
        return AgentChatResult(
            final_answer=CLEAR_CACHE_CONFIRMATION_PROMPT,
            tool_result={
                "requires_confirmation": True,
                "operation": "clear_cache",
            },
        )

    agent_result = run_langchain_agent(
        message=request.message,
        document_name=request.document_name,
        owner_id=owner_id,
    )
    return AgentChatResult(
        final_answer=agent_result["final_answer"],
        used_tools=agent_result.get("used_tools", []),
        tool_result={
            "agent_type": "langchain_tool_calling_agent",
            **agent_result.get("tool_result", {}),
        },
    )


def run_agent_chat(
    request: AgentChatRequest,
    background_tasks: BackgroundTasks,
    owner_id: int,
) -> AgentChatResult:
    start_time = time.perf_counter()
    result = _run_agent_chat_impl(
        request=request,
        background_tasks=background_tasks,
        owner_id=owner_id,
    )
    save_agent_chat_history(
        question=request.message.strip(),
        final_answer=result.final_answer,
        owner_id=owner_id,
        document_name=request.document_name,
        latency_ms=int((time.perf_counter() - start_time) * 1000),
    )
    return result
