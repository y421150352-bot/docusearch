from app.retrievers import vector_retriever
from app.services.qa_service import format_response


def _make_chunk(document_name: str, page_number: int, score: float, suffix: str) -> dict:
    return {
        "document_name": document_name,
        "page_number": page_number,
        "content": f"{document_name} page {page_number} content {suffix}",
        "score": score,
        "retrieval_type": "qdrant",
        "chunk_id": f"{document_name}_p{page_number}_c{suffix}",
    }


def test_retrieve_multi_document_chunks_balances_documents(monkeypatch):
    candidates = [
        _make_chunk("doc_a.pdf", 1, 0.99, "1"),
        _make_chunk("doc_a.pdf", 2, 0.98, "2"),
        _make_chunk("doc_a.pdf", 3, 0.97, "3"),
        _make_chunk("doc_b.pdf", 1, 0.96, "4"),
        _make_chunk("doc_b.pdf", 2, 0.95, "5"),
        _make_chunk("doc_c.pdf", 1, 0.94, "6"),
        _make_chunk("doc_c.pdf", 2, 0.93, "7"),
        _make_chunk("doc_d.pdf", 1, 0.92, "8"),
        _make_chunk("doc_e.pdf", 1, 0.91, "9"),
    ]

    monkeypatch.setattr(
        vector_retriever,
        "search_qdrant_index",
        lambda query, owner_id, top_k, document_name=None: candidates[:top_k],
    )

    results = vector_retriever.retrieve_multi_document_chunks(
        "这些文章主要研究了什么",
        owner_id=1,
        max_docs=4,
        chunks_per_doc=2,
    )

    document_names = [item["document_name"] for item in results]
    assert len(results) <= 8
    assert len(set(document_names)) >= 4
    assert document_names[:4] == [
        "doc_a.pdf",
        "doc_b.pdf",
        "doc_c.pdf",
        "doc_d.pdf",
    ]
    assert document_names.count("doc_a.pdf") <= 2


def test_format_response_balances_multi_document_sources():
    retrieved_chunks = [
        _make_chunk("doc_a.pdf", 1, 0.99, "1"),
        _make_chunk("doc_b.pdf", 2, 0.97, "2"),
        _make_chunk("doc_c.pdf", 3, 0.95, "3"),
        _make_chunk("doc_a.pdf", 4, 0.94, "4"),
        _make_chunk("doc_b.pdf", 5, 0.93, "5"),
        _make_chunk("doc_c.pdf", 6, 0.92, "6"),
    ]
    generated_result = {
        "summary": "综合来看，多篇文档共同指向认知负荷评估与应用问题。",
        "key_points": [
            {"title": "要点1", "content": "内容1"},
            {"title": "要点2", "content": "内容2"},
            {"title": "要点3", "content": "内容3"},
            {"title": "要点4", "content": "内容4"},
            {"title": "要点5", "content": "内容5"},
        ],
    }

    response = format_response(
        question="这些文章主要研究了什么？",
        generated_result=generated_result,
        retrieved_chunks=retrieved_chunks,
        multi_document_mode=True,
    )

    source_documents = [source.document_name for source in response.sources]
    assert len(response.sources) == 5
    assert len(set(source_documents)) >= 3
    assert source_documents.count("doc_a.pdf") <= 2
    assert source_documents.count("doc_b.pdf") <= 2
    assert source_documents.count("doc_c.pdf") <= 2
