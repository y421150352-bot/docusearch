import hashlib
import re
from collections import Counter

from qdrant_client import models


BM25_K1 = 1.5
BM25_B = 0.75


def tokenize_for_sparse(text: str) -> list[str]:
    """Tokenize mixed Chinese/ASCII text into words and Chinese 1/2-grams."""
    tokens: list[str] = []
    for segment in re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
            tokens.extend(segment)
            tokens.extend(
                segment[index : index + 2]
                for index in range(len(segment) - 1)
            )
        else:
            tokens.append(segment)
    return tokens


def _token_index(token: str) -> int:
    return int.from_bytes(
        hashlib.sha256(token.encode("utf-8")).digest()[:4],
        byteorder="big",
        signed=False,
    )


def _index_frequencies(text: str) -> Counter[int]:
    return Counter(_token_index(token) for token in tokenize_for_sparse(text))


def encode_document_sparse(
    text: str,
    average_document_length: float,
) -> models.SparseVector:
    frequencies = _index_frequencies(text)
    document_length = sum(frequencies.values())
    average_length = max(float(average_document_length), 1.0)
    normalization = BM25_K1 * (
        1.0 - BM25_B + BM25_B * document_length / average_length
    )
    ordered = sorted(frequencies.items())
    return models.SparseVector(
        indices=[index for index, _ in ordered],
        values=[
            frequency * (BM25_K1 + 1.0) / (frequency + normalization)
            for _, frequency in ordered
        ],
    )


def encode_query_sparse(text: str) -> models.SparseVector:
    frequencies = _index_frequencies(text)
    ordered = sorted(frequencies.items())
    return models.SparseVector(
        indices=[index for index, _ in ordered],
        values=[float(frequency) for _, frequency in ordered],
    )
