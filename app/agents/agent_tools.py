import json
from contextvars import ContextVar

from langchain_core.tools import tool

from app.config import EMBEDDING_META_FILE, QDRANT_COLLECTION_NAME
from app.generators.llm_client import chat_completion
from app.services.concurrent_service import run_parallel_tasks
from app.services.document_service import (
    get_document_detail,
    get_document_index_stats,
    list_documents,
)
from app.services.history_service import list_chat_history
from app.services.qa_service import answer_question, make_clean_quote, retrieve_relevant_chunks
from app.services.task_service import get_task_status
from app.retrievers.qdrant_client import get_qdrant_client
from app.services.document_chunk_service import count_document_chunks


_agent_owner_id: ContextVar[int] = ContextVar("agent_owner_id", default=0)


def set_agent_owner(owner_id: int):
    return _agent_owner_id.set(owner_id)


def reset_agent_owner(token) -> None:
    _agent_owner_id.reset(token)


def _owner_id() -> int:
    owner_id = _agent_owner_id.get()
    if owner_id <= 0:
        raise RuntimeError("缺少当前用户上下文")
    return owner_id


def _success_payload(**kwargs) -> str:
    return json.dumps({"success": True, **kwargs}, ensure_ascii=False)


def _error_payload(exc: Exception) -> str:
    return json.dumps(
        {
            "success": False,
            "error": str(exc),
        },
        ensure_ascii=False,
    )


@tool
def rag_qa_tool(question: str, document_name: str | None = None) -> str:
    """Answer knowledge-base questions. Set document_name for single-document QA."""
    try:
        result = answer_question(
            question=question,
            owner_id=_owner_id(),
            document_name=document_name,
            persist_history=False,
        )
        return _success_payload(data=result.model_dump())
    except Exception as exc:
        return _error_payload(exc)


@tool
def list_documents_tool() -> str:
    """List the knowledge-base documents."""
    try:
        documents = list_documents(_owner_id())
        return _success_payload(
            count=len(documents),
            documents=documents,
        )
    except Exception as exc:
        return _error_payload(exc)


@tool
def chat_history_tool(limit: int = 10) -> str:
    """List recent chat history records."""
    try:
        history = list_chat_history(owner_id=_owner_id(), limit=limit)
        return _success_payload(
            count=len(history),
            history=history,
        )
    except Exception as exc:
        return _error_payload(exc)


@tool
def task_status_tool(task_id: str) -> str:
    """Query task status by task_id."""
    try:
        task = get_task_status(task_id)
        if task is None:
            return _success_payload(
                found=False,
                message="未找到该任务，请检查 task_id 是否正确。",
            )
        return _success_payload(
            found=True,
            task=task,
        )
    except Exception as exc:
        return _error_payload(exc)


@tool
def document_detail_tool(document_name: str) -> str:
    """Query document metadata by document_name."""
    try:
        detail = get_document_detail(document_name, _owner_id())
        if detail is None:
            return _success_payload(
                found=False,
                message=f"未找到文档: {document_name}",
            )
        return _success_payload(
            found=True,
            document=detail,
        )
    except Exception as exc:
        return _error_payload(exc)


@tool
def index_health_tool() -> str:
    """Check index health status for the knowledge base."""
    try:
        owner_id = _owner_id()
        stats = get_document_index_stats(owner_id=owner_id)
        chunk_count = count_document_chunks(owner_id=owner_id)
        client = get_qdrant_client()
        qdrant_collection_exists = client.collection_exists(QDRANT_COLLECTION_NAME)
        qdrant_point_count = (
            int(client.get_collection(QDRANT_COLLECTION_NAME).points_count or 0)
            if qdrant_collection_exists
            else 0
        )

        return _success_payload(
            document_count=stats["document_count"],
            indexed_count=stats["indexed_count"],
            outdated_count=stats["outdated_count"],
            failed_count=stats["failed_count"],
            indexed_documents=stats["indexed_documents"],
            outdated_documents=stats["outdated_documents"],
            failed_documents=stats["failed_documents"],
            chunk_storage="mysql.document_chunk",
            qdrant_collection=QDRANT_COLLECTION_NAME,
            qdrant_collection_exists=qdrant_collection_exists,
            qdrant_point_count=qdrant_point_count,
            retrieval_mode="dense+sparse+rrf",
            embedding_meta_exists=EMBEDDING_META_FILE.exists(),
            chunk_count=chunk_count,
        )
    except Exception as exc:
        return _error_payload(exc)


@tool
def search_sources_tool(
    query: str,
    document_name: str | None = None,
    top_k: int = 5,
) -> str:
    """Search relevant source snippets only, without generating an answer."""
    try:
        results = retrieve_relevant_chunks(
            query=query,
            owner_id=_owner_id(),
            document_name=document_name,
            top_k=top_k,
        )
        sources = [
            {
                "document_name": chunk.get("document_name"),
                "page_number": chunk.get("page_number"),
                "score": chunk.get("score"),
                "rerank_score": chunk.get("rerank_score"),
                "retrieval_type": chunk.get("retrieval_type"),
                "quote": make_clean_quote(chunk.get("content", "")),
            }
            for chunk in results
        ]
        return _success_payload(
            count=len(sources),
            sources=sources,
        )
    except Exception as exc:
        return _error_payload(exc)


@tool
def summarize_document_tool(document_name: str) -> str:
    """Summarize one document using the existing QA service."""
    try:
        result = answer_question(
            question="请总结这篇文档的主要内容",
            owner_id=_owner_id(),
            document_name=document_name,
            use_cache=False,
            persist_cache=False,
            persist_history=False,
        )
        return _success_payload(
            document_name=document_name,
            summary=result.model_dump(),
        )
    except Exception as exc:
        return _error_payload(exc)


def _build_compare_messages(
    document_a: str,
    document_b: str,
    summary_a: str,
    summary_b: str,
    question: str | None,
) -> list[dict]:
    compare_question = question or "请比较这两篇文档的主要异同，重点说明研究方法、研究对象、结论差异。"
    return [
        {
            "role": "system",
            "content": (
                "你是文档比较助手。你只能根据提供的两篇文档摘要做比较，不要补充外部知识。"
                "请用中文给出简洁、结构化的比较结论。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"比较问题：{compare_question}\n\n"
                f"文档A：{document_a}\n摘要A：{summary_a}\n\n"
                f"文档B：{document_b}\n摘要B：{summary_b}\n\n"
                "请输出一段比较结论，至少覆盖共同点、差异点、结论。"
            ),
        },
    ]


@tool
def compare_documents_tool(
    document_a: str,
    document_b: str,
    question: str | None = None,
) -> str:
    """Compare two documents by generating per-document summaries first."""
    try:
        per_doc_question = (
            f"请围绕这个比较问题，总结这篇文档中最相关的内容：{question}"
            if question
            else "请总结这篇文档的主要内容，重点说明研究方法、研究对象和结论。"
        )
        parallel_results = run_parallel_tasks(
            tasks=[
                lambda: answer_question(
                    question=per_doc_question,
                    owner_id=_owner_id(),
                    document_name=document_a,
                    use_cache=False,
                    persist_cache=False,
                    persist_history=False,
                ).model_dump(),
                lambda: answer_question(
                    question=per_doc_question,
                    owner_id=_owner_id(),
                    document_name=document_b,
                    use_cache=False,
                    persist_cache=False,
                    persist_history=False,
                ).model_dump(),
            ],
            max_workers=2,
        )

        if not parallel_results[0]["success"]:
            raise RuntimeError(f"{document_a} 摘要生成失败: {parallel_results[0]['error']}")
        if not parallel_results[1]["success"]:
            raise RuntimeError(f"{document_b} 摘要生成失败: {parallel_results[1]['error']}")

        summary_a = parallel_results[0]["result"]
        summary_b = parallel_results[1]["result"]
        comparison_prompt_result = chat_completion(
            _build_compare_messages(
                document_a=document_a,
                document_b=document_b,
                summary_a=summary_a.get("summary", ""),
                summary_b=summary_b.get("summary", ""),
                question=question,
            )
        )

        return _success_payload(
            document_a=document_a,
            document_b=document_b,
            question=question,
            summary_a=summary_a,
            summary_b=summary_b,
            comparison_prompt_result=comparison_prompt_result,
        )
    except Exception as exc:
        return _error_payload(exc)


def get_agent_tools() -> list:
    return [
        rag_qa_tool,
        list_documents_tool,
        chat_history_tool,
        task_status_tool,
        document_detail_tool,
        index_health_tool,
        search_sources_tool,
        summarize_document_tool,
        compare_documents_tool,
    ]
