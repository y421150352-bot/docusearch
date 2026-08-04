import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INDEX_DIR = DATA_DIR / "index"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://docusearch:123456@127.0.0.1:3307/docusearch?charset=utf8mb4",
)

CHUNK_SIZE = 900
OVERLAP = 2
TOP_K = 6
MAX_CONTEXT_CHUNKS = 4

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = _get_int_env("LLM_TIMEOUT", 60)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = _get_int_env("REDIS_PORT", 6379)
REDIS_DB = _get_int_env("REDIS_DB", 0)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
CACHE_TTL_SECONDS = _get_int_env("CACHE_TTL_SECONDS", 3600)
TASK_STATUS_TTL_SECONDS = _get_int_env("TASK_STATUS_TTL_SECONDS", 86400)

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
# The model has already been downloaded during local setup.  Defaulting to
# local-only prevents an unnecessary Hugging Face network request on every
# backend restart; set this to false in .env only when intentionally updating.
EMBEDDING_LOCAL_FILES_ONLY = _get_bool_env("EMBEDDING_LOCAL_FILES_ONLY", True)
USE_QDRANT_RETRIEVAL = _get_bool_env("USE_QDRANT_RETRIEVAL", True)
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "docusearch_chunks")
QDRANT_TIMEOUT = _get_int_env("QDRANT_TIMEOUT", 30)
USE_RERANKER = _get_bool_env("USE_RERANKER", False)
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-base")
RERANKER_LOCAL_FILES_ONLY = _get_bool_env("RERANKER_LOCAL_FILES_ONLY", False)
RERANK_TOP_N = _get_int_env("RERANK_TOP_N", 8)
RERANK_CANDIDATE_TOP_K = _get_int_env("RERANK_CANDIDATE_TOP_K", 30)
EMBEDDING_META_FILE = INDEX_DIR / "embedding_meta.json"


def is_llm_configured() -> bool:
    return bool(LLM_API_KEY.strip())
