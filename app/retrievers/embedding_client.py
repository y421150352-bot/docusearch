# import os
from functools import lru_cache

# os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_LOCAL_FILES_ONLY, EMBEDDING_MODEL_NAME


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    加载 embedding 模型。

    可通过 EMBEDDING_LOCAL_FILES_ONLY 控制是否仅使用本地缓存。
    """
    print(f">>> LOAD EMBEDDING MODEL: {EMBEDDING_MODEL_NAME}")

    return SentenceTransformer(
        EMBEDDING_MODEL_NAME,
        local_files_only=EMBEDDING_LOCAL_FILES_ONLY,
    )


def encode_texts(texts: list[str]):
    """
    将多段文本转换成 embedding 向量。

    normalize_embeddings=True：
    对向量归一化。
    归一化后的向量写入 Qdrant，并使用 cosine similarity 检索。
    """
    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    return embeddings


def encode_query(query: str):
    """
    将用户问题转换成 query embedding。
    """
    model = get_embedding_model()

    embedding = model.encode(
        [query],
        normalize_embeddings=True,
    )

    return embedding
