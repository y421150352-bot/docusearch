import asyncio
import json
import re
from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

from app.services.qa_service import answer_question


STREAM_CHUNK_SIZE = 16


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _split_summary(summary: str, chunk_size: int = STREAM_CHUNK_SIZE) -> list[str]:
    text = re.sub(r"\s+", " ", summary).strip()
    if not text:
        return []

    punctuation = set("，。！？；,.!?;:")
    chunks: list[str] = []
    current = ""

    for character in text:
        current += character
        if len(current) >= chunk_size and character in punctuation:
            chunks.append(current)
            current = ""
        elif len(current) >= chunk_size:
            chunks.append(current)
            current = ""

    if current:
        chunks.append(current)
    return chunks


async def _stream_answer_events(
    question: str,
    document_name: str | None,
    owner_id: int,
) -> AsyncIterator[str]:
    try:
        yield _sse_event("status", {"message": "Starting retrieval..."})
        await asyncio.sleep(0)

        # Keep SSE responsive even though the current RAG pipeline is
        # synchronous and returns a finalized answer payload.
        response = await asyncio.to_thread(
            answer_question,
            question=question,
            document_name=document_name,
            owner_id=owner_id,
        )

        yield _sse_event("status", {"message": "Answer generated. Streaming response..."})
        await asyncio.sleep(0)

        for chunk in _split_summary(response.summary):
            yield _sse_event("token", {"content": chunk})
            await asyncio.sleep(0)

        yield _sse_event(
            "done",
            {
                "question": response.question,
                "summary": response.summary,
                "sources": [source.model_dump() for source in response.sources],
                "key_points": [item.model_dump() for item in response.key_points],
            },
        )
    except Exception as exc:
        yield _sse_event("error", {"message": str(exc)})


def stream_answer(
    question: str,
    document_name: str | None = None,
    owner_id: int = 0,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_answer_events(question=question, document_name=document_name, owner_id=owner_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
