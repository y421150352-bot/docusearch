from collections import OrderedDict
from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT
from app.generators.llm_client import chat_completion


def build_context_text(retrieved_chunks: list[dict], max_context_chunks: int = 4) -> str:
    context_parts = []
    for chunk in retrieved_chunks[:max_context_chunks]:
        context_parts.append(
            f"[Document] {chunk['document_name']}\n"
            f"[Page] {chunk['page_number']}\n"
            f"[Content] {chunk['content']}"
        )
    return "\n\n".join(context_parts)


def build_multi_document_context_text(retrieved_chunks: list[dict]) -> str:
    grouped_chunks: OrderedDict[str, list[dict]] = OrderedDict()
    for chunk in retrieved_chunks:
        grouped_chunks.setdefault(chunk["document_name"], []).append(chunk)

    context_parts = []
    for document_index, (document_name, chunks) in enumerate(grouped_chunks.items(), start=1):
        document_parts = [f"[Document {document_index}] {document_name}"]
        for source_index, chunk in enumerate(chunks, start=1):
            document_parts.append(
                f"[Source {source_index}] page={chunk['page_number']} score={chunk.get('score', 0)} retrieval={chunk.get('retrieval_type', 'unknown')}\n"
                f"{chunk['content']}"
            )
        context_parts.append("\n".join(document_parts))
    return "\n\n".join(context_parts)


def _normalize_openai_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def _build_llm() -> ChatOpenAI:
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is empty")

    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=_normalize_openai_base_url(LLM_BASE_URL),
        timeout=LLM_TIMEOUT,
        temperature=0.2,
        max_retries=2,
    )


def _shared_prompt_rules() -> str:
    return (
        "你是面向研究生和科研人员的私有知识库学术助手。"
        "你的回答要深入、系统、结构清晰，适合用于论文阅读、课题学习、实验设计和研究综述。\n"
        "回答原则：\n"
        "1. 不要只做简单概括，也不要机械地说“多篇文档共同表明”。\n"
        "2. 你必须根据问题类型组织回答：\n"
        "   - 问“是什么”：重点解释概念、定义、分类、背景和研究意义。\n"
        "   - 问“怎么做 / 怎么构建 / 如何建立 / 如何实现”：必须回答方法流程、关键步骤、输入输出和可操作方案。\n"
        "   - 问“有什么区别 / 对比”：必须按维度比较理论、数据、方法、优缺点和适用场景。\n"
        "   - 问“论文怎么写 / 实验怎么做”：必须给研究路线、实验设计、模型路线和评价指标。\n"
        "3. 对“怎么构建 / 怎么建立 / 怎么实现”类问题，优先按以下结构回答：\n"
        "   ## 1. 概念与目标\n"
        "   ## 2. 理论依据\n"
        "   ## 3. 可观测信号或数据来源\n"
        "   ## 4. 数据采集与预处理\n"
        "   ## 5. 特征构建\n"
        "   ## 6. 标签或负荷等级构建\n"
        "   ## 7. 模型建立\n"
        "   ## 8. 评价指标\n"
        "   ## 9. 应用与局限\n"
        "4. 回答要优先综合成完整研究框架，再说明哪些文档支持哪个环节。\n"
        "5. 如果文档证据不足，要明确写“文档中未充分说明”。你可以基于已有材料做合理研究框架归纳，"
        "但必须明确标注“以下内容属于基于现有材料的归纳推导”。\n"
        "6. summary 可以使用 Markdown 结构化长回答，允许标题、编号、列表和加粗。\n"
        "7. key_points 必须给 5 到 8 条，每条都要有明确标题和具体解释，不能只是短语。\n"
        "8. 回答长度要求：普通问题约 400 到 800 字；方法构建类、对比类、综述类约 800 到 1500 字。\n"
        "9. summary 正文中禁止插入任何引用标记。不要出现类似 ([Document 1, Source 1])、[Document 1]、Source 1、(Source 2) 这样的标记。\n"
        "10. key_points 中也禁止插入任何 Document / Source 引用标记。\n"
        "11. 引用来源由系统单独在 sources 字段中返回，不要写进 summary 和 key_points。\n"
        "12. 只能基于提供的上下文作答，不要编造上下文中完全没有支持的具体事实、数字、实验结果或文献结论。\n"
        "13. 使用严谨、克制的学术写作风格，禁止使用 emoji、颜文字或装饰性图标。\n"
        "14. 数学公式必须使用标准 LaTeX：行内公式写作 $...$，独立公式写作 $$...$$，不要使用 Unicode 字符拼凑公式。\n"
        "15. 返回 JSON 且只能返回 JSON。"
    )


def _build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                _shared_prompt_rules()
                + "\n"
                + "当前是单文档或常规 RAG 问答场景。"
                + "回答正文要自然、连续、直接回答用户问题，不要在正文中插入来源标记。"
                + "如果文档只覆盖部分环节，要明确说明文档主要涉及哪些部分。"
                + "严格输出 JSON，格式示例："
                + '{{'
                + '"summary":"结构化长回答",'
                + '"key_points":['
                + '{{"title":"要点1","content":"具体解释1"}},'
                + '{{"title":"要点2","content":"具体解释2"}}'
                + "]"
                + "}}",
            ),
            (
                "human",
                "问题：{question}\n\n"
                "上下文：\n{context}\n\n"
                "输出要求：\n"
                "1. summary 必须直接回答问题，并尽量形成概念、方法、实验、应用的完整框架。\n"
                "2. 如果问题属于“怎么构建 / 怎么建立 / 怎么实现”，优先使用九段式结构。\n"
                "3. 不要在 summary 和 key_points 中写任何 Document / Source 引用标记。\n"
                "4. 如果上下文只覆盖部分环节，要明确指出“文档主要涉及哪些部分”。\n"
                "5. 如果证据不足，要明确标注“文档中未充分说明”以及“以下内容属于基于现有材料的归纳推导”。\n"
                "6. key_points 必须包含 5 到 8 条。\n"
                "7. 只能返回 JSON。",
            ),
        ]
    )


def _build_multi_doc_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                _shared_prompt_rules()
                + "\n"
                + "当前是多文档综合问答场景。"
                + "你需要先把多篇文档整合成清晰框架，再说明不同文档分别支持哪个部分。"
                + "不要机械重复“多篇文档共同表明”，而要形成综述式讲解。"
                + "回答正文要自然、连续、直接回答问题，不要在 summary 和 key_points 中插入来源标记。"
                + "严格输出 JSON，格式示例："
                + '{{'
                + '"summary":"结构化长回答",'
                + '"key_points":['
                + '{{"title":"要点1","content":"具体解释1"}},'
                + '{{"title":"要点2","content":"具体解释2"}}'
                + "]"
                + "}}",
            ),
            (
                "human",
                "问题：{question}\n\n"
                "多文档上下文：\n{context}\n\n"
                "输出要求：\n"
                "1. 先给出综合框架，再指出不同文档分别支持理论定义、信号特征、模型构建、实验结论或应用价值中的哪些部分。\n"
                "2. 如果问题属于方法构建类、综述类或对比类，summary 应尽量达到 800 到 1500 字。\n"
                "3. 不要在 summary 和 key_points 中写任何 Document / Source 引用标记。\n"
                "4. 如果证据不足，明确指出哪些环节文档中未充分说明，并把补充框架标注为“基于现有材料的归纳推导”。\n"
                "5. key_points 必须包含 5 到 8 条。\n"
                "6. 只能返回 JSON。",
            ),
        ]
    )


def _prompt_value_to_openai_messages(prompt_value) -> list[dict]:
    messages = []

    for message in prompt_value.to_messages():
        message_type = getattr(message, "type", "")
        role = "user"

        if message_type == "system":
            role = "system"
        elif message_type == "ai":
            role = "assistant"

        messages.append(
            {
                "role": role,
                "content": message.content,
            }
        )

    return messages


def run_langchain_rag_qa(
    question: str,
    retrieved_chunks: list[dict],
    max_context_chunks: int = 4,
) -> str:
    print(">>> USING LANGCHAIN LCEL RAG CHAIN <<<")

    prompt = _build_prompt()
    llm = _build_llm()
    output_parser = StrOutputParser()

    chain = (
        {
            "question": itemgetter("question"),
            "context": RunnableLambda(
                lambda payload: build_context_text(
                    payload["retrieved_chunks"],
                    max_context_chunks=payload["max_context_chunks"],
                )
            ),
        }
        | prompt
        | llm
        | output_parser
    )

    fallback_chain = (
        {
            "question": itemgetter("question"),
            "context": RunnableLambda(
                lambda payload: build_context_text(
                    payload["retrieved_chunks"],
                    max_context_chunks=payload["max_context_chunks"],
                )
            ),
        }
        | prompt
        | RunnableLambda(
            lambda prompt_value: chat_completion(
                _prompt_value_to_openai_messages(prompt_value)
            )
        )
        | output_parser
    )

    payload = {
        "question": question,
        "retrieved_chunks": retrieved_chunks,
        "max_context_chunks": max_context_chunks,
    }

    try:
        return chain.invoke(payload)
    except Exception as exc:
        print(f">>> LANGCHAIN CHATOPENAI FAILED, FALLBACK TO LEGACY CLIENT: {repr(exc)}")
        return fallback_chain.invoke(payload)


def run_langchain_multi_doc_rag_qa(
    question: str,
    retrieved_chunks: list[dict],
) -> str:
    print(">>> USING LANGCHAIN LCEL MULTI-DOCUMENT RAG CHAIN <<<")

    prompt = _build_multi_doc_prompt()
    llm = _build_llm()
    output_parser = StrOutputParser()

    chain = (
        {
            "question": itemgetter("question"),
            "context": RunnableLambda(
                lambda payload: build_multi_document_context_text(payload["retrieved_chunks"])
            ),
        }
        | prompt
        | llm
        | output_parser
    )

    fallback_chain = (
        {
            "question": itemgetter("question"),
            "context": RunnableLambda(
                lambda payload: build_multi_document_context_text(payload["retrieved_chunks"])
            ),
        }
        | prompt
        | RunnableLambda(
            lambda prompt_value: chat_completion(
                _prompt_value_to_openai_messages(prompt_value)
            )
        )
        | output_parser
    )

    payload = {
        "question": question,
        "retrieved_chunks": retrieved_chunks,
    }

    try:
        return chain.invoke(payload)
    except Exception as exc:
        print(f">>> LANGCHAIN CHATOPENAI FAILED, FALLBACK TO LEGACY CLIENT: {repr(exc)}")
        return fallback_chain.invoke(payload)
