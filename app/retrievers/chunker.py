import re


SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？；.!?;])")


def split_into_sentences(text: str) -> list[str]:
    parts = SENTENCE_SPLIT_PATTERN.split(text)
    sentences = [part.strip() for part in parts if part and part.strip()]
    return sentences


def split_text_into_chunks(
    text: str,
    chunk_size: int = 900,
    overlap: int = 2,
) -> list[str]:
    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    sentences = split_into_sentences(text.strip())
    if not sentences:
        return []

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)

        if sentence_length >= chunk_size:
            if current_sentences:
                chunks.append("".join(current_sentences).strip())
                current_sentences = []
                current_length = 0
            chunks.append(sentence.strip())
            continue

        if current_sentences and current_length + sentence_length > chunk_size:
            chunks.append("".join(current_sentences).strip())
            overlap_sentences = current_sentences[-overlap:] if overlap > 0 else []
            current_sentences = overlap_sentences.copy()
            current_length = sum(len(item) for item in current_sentences)

        current_sentences.append(sentence)
        current_length += sentence_length

    if current_sentences:
        chunks.append("".join(current_sentences).strip())

    return [chunk for chunk in chunks if chunk]


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 900,
    overlap: int = 2,
) -> list[dict]:
    all_chunks = []

    for document in documents:
        text_chunks = split_text_into_chunks(
            document["content"],
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for index, chunk_text in enumerate(text_chunks, start=1):
            all_chunks.append(
                {
                    "document_name": document["document_name"],
                    "page_number": document["page_number"],
                    "chunk_id": (
                        f'{document["document_name"]}_p{document["page_number"]}_c{index}'
                    ),
                    "content": chunk_text,
                }
            )

    return all_chunks
