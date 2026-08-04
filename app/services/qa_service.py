import json
import re
import time
from collections import OrderedDict

from app.chains.rag_qa_chain import (
    run_langchain_multi_doc_rag_qa,
    run_langchain_rag_qa,
)
from app.config import (
    MAX_CONTEXT_CHUNKS,
    RERANK_CANDIDATE_TOP_K,
    RERANK_TOP_N,
    TOP_K,
)
from app.retrievers.vector_retriever import (
    hybrid_search_candidates,
    rerank_or_fallback,
    retrieve_multi_document_chunks,
)
from app.schemas.response_schema import AnswerResponse, KeyPoint, SourceItem
from app.services.cache_service import get_cached_answer, set_cached_answer
from app.services.history_service import save_chat_history


MAX_SINGLE_SOURCES = 3
MAX_MULTI_SOURCES = 5
MAX_MULTI_SOURCES_PER_DOC = 2
MAX_QUOTE_LENGTH = 280
MULTI_DOC_MAX_DOCS = 4
MULTI_DOC_CHUNKS_PER_DOC = 3


def normalize_query(question: str) -> str:
    return question.strip()


def is_multi_document_mode(document_name: str | None) -> bool:
    return not (document_name or "").strip()


def retrieve_relevant_chunks(
    query: str,
    owner_id: int,
    document_name: str | None = None,
    top_k: int = TOP_K,
) -> list[dict]:
    candidate_top_k = max(RERANK_CANDIDATE_TOP_K, top_k)
    candidates = hybrid_search_candidates(
        query=query,
        owner_id=owner_id,
        document_name=document_name,
        candidate_top_k=candidate_top_k,
    )
    if candidates:
        return rerank_or_fallback(
            query=query,
            candidates=candidates,
            top_n=top_k,
        )

    return []


def parse_llm_result(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("invalid llm json")
        return data
    except Exception:
        return {
            "summary": raw_text.strip(),
            "key_points": [
                {
                    "title": "模型原始输出",
                    "content": raw_text.strip(),
                }
            ],
        }


INLINE_CITATION_PATTERNS = [
    re.compile(r"[（(]?\s*\[?\s*Document\s*\d+\s*,\s*Source\s*\d+\s*\]?\s*[)）]?", re.IGNORECASE),
    re.compile(r"[（(]?\s*Document\s*\d+\s*,\s*Source\s*\d+\s*[)）]?", re.IGNORECASE),
    re.compile(r"[（(]?\s*\[?\s*Source\s*\d+\s*\]?\s*[)）]?", re.IGNORECASE),
    re.compile(r"\[\s*Document\s*\d+\s*\]", re.IGNORECASE),
]


def clean_inline_citations(text: str) -> str:
    cleaned = text
    for pattern in INLINE_CITATION_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+([，。！？；：,.!?;:])", r"\1", cleaned)
    return cleaned.strip()


def _truncate_text(text: str, max_length: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_length:
        return compact
    return compact[:max_length].rstrip() + "..."


def _fallback_key_points(retrieved_chunks: list[dict], min_points: int = 5) -> list[dict]:
    key_points = []
    for index, chunk in enumerate(retrieved_chunks[:min_points], start=1):
        key_points.append(
            {
                "title": f"关键信息 {index}",
                "content": _truncate_text(chunk["content"], 160),
            }
        )

    while len(key_points) < min_points and retrieved_chunks:
        key_points.append(
            {
                "title": f"补充信息 {len(key_points) + 1}",
                "content": _truncate_text(retrieved_chunks[0]["content"], 160),
            }
        )

    return key_points


def _empty_answer(question: str, multi_document_mode: bool) -> dict:
    if multi_document_mode:
        return {
            "summary": (
                f"当前知识库中没有检索到与“{question}”直接相关且足以支撑多文档综合回答的内容。"
                "全部文档模式下，系统需要至少从多篇材料中提取可比较的证据；但本次命中的上下文不足，"
                "因此无法可靠归纳多篇文档的共同观点、差异和结论。建议改用更明确的关键词、研究对象、方法名"
                "或文档标题重新提问，或先补充相关文档并重建索引。"
            ),
            "key_points": [
                {
                    "title": "未命中有效证据",
                    "content": "当前没有检索到足够相关的多文档片段，无法形成可靠的综合结论。",
                },
                {
                    "title": "不能脱离材料生成",
                    "content": "系统被限制为只能依据已检索到的上下文回答，不会在证据不足时补充外部知识。",
                },
                {
                    "title": "建议优化提问方式",
                    "content": "可以改用更具体的研究主题、术语、指标、方法名或文档标题来提升检索命中率。",
                },
                {
                    "title": "建议补充文档",
                    "content": "如果相关材料尚未上传或尚未完成索引重建，建议先补充文档并重新构建索引。",
                },
                {
                    "title": "当前证据有限",
                    "content": "全部文档模式强调跨文档综合；在证据不足时，系统会明确说明限制而不是强行归纳。",
                },
            ],
        }

    return {
        "summary": (
            f"当前知识库中没有检索到与“{question}”直接相关且足以支撑完整回答的内容。"
            "系统暂时无法基于现有材料给出可靠结论。建议尝试更具体的关键词、文档标题或主题词，"
            "或者先补充相关文档并重建索引后再提问。"
        ),
        "key_points": [
            {
                "title": "未命中有效证据",
                "content": "本次检索没有找到足够相关的文本片段，因此无法输出基于证据的完整回答。",
            },
            {
                "title": "不能脱离材料编造",
                "content": "系统只能依据检索到的上下文回答，在证据不足时会明确说明，而不是补充外部知识。",
            },
            {
                "title": "建议调整提问方式",
                "content": "可以尝试使用更明确的术语、文档标题、主题词或关键概念，以提升检索命中率。",
            },
            {
                "title": "建议补充索引数据",
                "content": "如果相关文档尚未上传或尚未完成索引重建，建议先补充文档并重新执行索引任务。",
            },
        ],
    }


def generate_answer(
    normalized_question: str,
    retrieved_chunks: list[dict],
    multi_document_mode: bool = False,
) -> dict:
    if not retrieved_chunks:
        return _empty_answer(normalized_question, multi_document_mode=multi_document_mode)

    try:
        if multi_document_mode:
            print(">>> GENERATION: LangChain Multi-document RAG Chain")
            raw_result = run_langchain_multi_doc_rag_qa(
                question=normalized_question,
                retrieved_chunks=retrieved_chunks,
            )
            minimum_key_points = 6
            maximum_key_points = 8
        else:
            print(">>> GENERATION: LangChain Single-document RAG Chain")
            raw_result = run_langchain_rag_qa(
                question=normalized_question,
                retrieved_chunks=retrieved_chunks,
                max_context_chunks=MAX_CONTEXT_CHUNKS,
            )
            minimum_key_points = 5
            maximum_key_points = 8
        parsed_result = parse_llm_result(raw_result)
    except Exception as exc:
        parsed_result = {
            "summary": (
                "本次回答生成阶段出现异常，因此系统只能根据已检索到的上下文返回保守结果。"
                f"当前错误信息为：{exc}。以下内容仅概括最相关片段，不代表完整结论。"
            ),
            "key_points": _fallback_key_points(
                retrieved_chunks,
                min_points=6 if multi_document_mode else 5,
            ),
        }
        minimum_key_points = 6 if multi_document_mode else 5
        maximum_key_points = 8

    if not isinstance(parsed_result.get("summary"), str):
        parsed_result["summary"] = "模型未返回有效的 summary。"

    key_points = parsed_result.get("key_points")
    if not isinstance(key_points, list):
        key_points = []

    normalized_key_points = []
    for item in key_points[:maximum_key_points]:
        if isinstance(item, dict):
            title = str(item.get("title", "Key Point")).strip() or "Key Point"
            content = str(item.get("content", "")).strip()
            if content:
                normalized_key_points.append({"title": title, "content": content})

    if len(normalized_key_points) < minimum_key_points:
        normalized_key_points = _fallback_key_points(
            retrieved_chunks,
            min_points=minimum_key_points,
        )

    parsed_result["summary"] = clean_inline_citations(parsed_result["summary"].strip())
    parsed_result["key_points"] = [
        {
            "title": clean_inline_citations(item["title"]),
            "content": clean_inline_citations(item["content"]),
        }
        for item in normalized_key_points[:maximum_key_points]
    ]
    return parsed_result


def _find_best_cutoff(text: str, max_length: int) -> int:
    if len(text) <= max_length:
        return len(text)

    punctuation_positions = [
        text.rfind(symbol, 0, max_length)
        for symbol in ["。", "，", "；", "：", ".", "!", "?", ";"]
    ]
    best_position = max(punctuation_positions)
    if best_position >= int(max_length * 0.6):
        return best_position + 1

    return max_length


def make_clean_quote(text: str, max_length: int = MAX_QUOTE_LENGTH) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_length:
        return compact

    cutoff = _find_best_cutoff(compact, max_length)
    quote = compact[:cutoff].strip()
    if cutoff < len(compact):
        quote += "..."
    return quote


def _select_balanced_source_chunks(retrieved_chunks: list[dict]) -> list[dict]:
    grouped_chunks: OrderedDict[str, list[dict]] = OrderedDict()
    for chunk in retrieved_chunks:
        document_name = chunk["document_name"]
        selected = grouped_chunks.setdefault(document_name, [])
        if len(selected) >= MAX_MULTI_SOURCES_PER_DOC:
            continue
        selected.append(chunk)

    balanced_chunks: list[dict] = []
    for chunk_index in range(MAX_MULTI_SOURCES_PER_DOC):
        for chunks in grouped_chunks.values():
            if chunk_index < len(chunks):
                balanced_chunks.append(chunks[chunk_index])
                if len(balanced_chunks) >= MAX_MULTI_SOURCES:
                    return balanced_chunks
    return balanced_chunks


def format_response(
    question: str,
    generated_result: dict,
    retrieved_chunks: list[dict],
    multi_document_mode: bool = False,
) -> AnswerResponse:
    key_points = [
        KeyPoint(title=item["title"], content=item["content"])
        for item in generated_result["key_points"]
    ]

    source_chunks = (
        _select_balanced_source_chunks(retrieved_chunks)
        if multi_document_mode
        else retrieved_chunks[:MAX_SINGLE_SOURCES]
    )
    sources = [
        SourceItem(
            document_name=chunk["document_name"],
            page_number=chunk["page_number"],
            quote=make_clean_quote(chunk["content"]),
            score=chunk.get("score"),
            rerank_score=chunk.get("rerank_score"),
            retrieval_type=chunk.get("retrieval_type"),
        )
        for chunk in source_chunks
    ]

    return AnswerResponse(
        question=question,
        summary=generated_result["summary"],
        key_points=key_points,
        sources=sources,
    )


def is_fallback_answer(answer: dict) -> bool:
    summary = str(answer.get("summary", "")).lower()
    fallback_keywords = ["failed", "fallback", "timed out", "timeout", "异常"]
    return any(keyword in summary for keyword in fallback_keywords)


def answer_question(
    question: str,
    owner_id: int,
    document_name: str | None = None,
    use_cache: bool = True,
    persist_cache: bool = True,
    persist_history: bool = True,
) -> AnswerResponse:
    start_time = time.perf_counter()
    multi_document_mode = is_multi_document_mode(document_name)

    cached_result = (
        get_cached_answer(question, owner_id, document_name) if use_cache else None
    )
    if cached_result:
        final_response = AnswerResponse(**cached_result)
        if persist_history:
            save_chat_history(
                question=question,
                response=final_response,
                owner_id=owner_id,
                document_name=document_name,
                from_cache=True,
                latency_ms=int((time.perf_counter() - start_time) * 1000),
            )
        return final_response

    normalized_question = normalize_query(question)

    if multi_document_mode:
        print(">>> RAG MODE: multi document")
        retrieved_chunks = retrieve_multi_document_chunks(
            normalized_question,
            owner_id=owner_id,
            max_docs=MULTI_DOC_MAX_DOCS,
            chunks_per_doc=MULTI_DOC_CHUNKS_PER_DOC,
        )
    else:
        print(">>> RAG MODE: single document")
        retrieved_chunks = retrieve_relevant_chunks(
            normalized_question,
            owner_id=owner_id,
            document_name=document_name,
            top_k=max(TOP_K, RERANK_TOP_N),
        )

    generated_result = generate_answer(
        normalized_question,
        retrieved_chunks,
        multi_document_mode=multi_document_mode,
    )
    final_response = format_response(
        question,
        generated_result,
        retrieved_chunks,
        multi_document_mode=multi_document_mode,
    )

    if persist_cache and not is_fallback_answer(generated_result):
        set_cached_answer(
            question,
            final_response.model_dump(),
            owner_id,
            document_name,
        )

    if persist_history:
        save_chat_history(
            question=question,
            response=final_response,
            owner_id=owner_id,
            document_name=document_name,
            from_cache=False,
            latency_ms=int((time.perf_counter() - start_time) * 1000),
        )
    return final_response
