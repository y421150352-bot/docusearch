from app.retrievers.sparse_encoder import (
    encode_document_sparse,
    encode_query_sparse,
    tokenize_for_sparse,
)


def test_sparse_bm25_encoder_is_deterministic() -> None:
    text = "飞行训练中的认知负荷评估依赖主观量表和生理信号"
    document_vector = encode_document_sparse(text, average_document_length=30)
    query_vector = encode_query_sparse("飞行训练 认知负荷")

    assert tokenize_for_sparse(text)
    assert document_vector.indices == sorted(document_vector.indices)
    assert query_vector.indices == sorted(query_vector.indices)
    assert set(query_vector.indices) & set(document_vector.indices)
