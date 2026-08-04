from app.config import CHUNK_SIZE, OVERLAP, RAW_DIR
import re

from app.loaders.document_loader import load_documents_from_directory
from app.loaders.document_loader import load_document
from app.retrievers.chunker import chunk_documents
from app.services.document_chunk_service import replace_document_chunks


SUPPORTED_INDEX_SUFFIXES = {".pdf", ".txt", ".md"}


def is_noise_chunk(text: str) -> bool:
    normalized = text.strip()
    lower_text = normalized.lower()
    if len(normalized) < 30:
        return True
    if "doi" in lower_text or "fig." in lower_text or "http" in lower_text:
        return True

    # A table of contents may span chunks even after individual dotted lines
    # are removed.  Do not store it in either MySQL or Qdrant.
    if "目录" in normalized or re.search(r"\bcontents\b", normalized, re.IGNORECASE):
        return True
    dot_leader_count = len(re.findall(r"(?:\.{5,}|…{3,}|·{5,})\s*\d+", normalized))
    return dot_leader_count >= 1


def parse_chunks_from_directory(
    raw_dir: str = str(RAW_DIR),
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> list[dict]:
    documents = load_documents_from_directory(raw_dir)
    chunks = chunk_documents(documents, chunk_size=chunk_size, overlap=overlap)
    chunks = [
        chunk
        for chunk in chunks
        if any(
            str(chunk["document_name"]).lower().endswith(suffix)
            for suffix in SUPPORTED_INDEX_SUFFIXES
        )
        and not is_noise_chunk(str(chunk["content"]))
    ]
    if not chunks:
        raise ValueError("没有可用于构建索引的文本片段。")
    return chunks


def parse_chunks_from_file(
    file_path: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> list[dict]:
    chunks = chunk_documents(
        load_document(file_path),
        chunk_size=chunk_size,
        overlap=overlap,
    )
    chunks = [
        chunk
        for chunk in chunks
        if not is_noise_chunk(str(chunk["content"]))
    ]
    if not chunks:
        raise ValueError("该文档没有可用于问答的文本片段。")
    return chunks


def build_index_from_directory(
    raw_dir: str = str(RAW_DIR),
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> int:
    chunks = parse_chunks_from_directory(raw_dir, chunk_size, overlap)
    return replace_document_chunks(chunks)
