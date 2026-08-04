from pathlib import Path

from sqlalchemy import text

from app.cache.redis_client import get_redis_client
from app.config import (
    DATABASE_URL,
    INDEX_DIR,
    QDRANT_COLLECTION_NAME,
    RAW_DIR,
    is_llm_configured,
)
from app.db.database import engine
from app.retrievers.qdrant_client import get_qdrant_client
from app.services.document_chunk_service import count_document_chunks


def _build_component(name: str, ok: bool, detail: str, critical: bool) -> dict:
    return {
        "name": name,
        "ok": ok,
        "detail": detail,
        "critical": critical,
    }


def _check_database() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return _build_component(
            name="database",
            ok=True,
            detail=f"mysql ready: {DATABASE_URL.split('@')[-1]}",
            critical=True,
        )
    except Exception as exc:
        return _build_component(
            name="database",
            ok=False,
            detail=f"mysql unavailable: {exc}",
            critical=True,
        )


def _check_redis() -> dict:
    try:
        get_redis_client().ping()
        return _build_component(
            name="redis",
            ok=True,
            detail="redis reachable",
            critical=True,
        )
    except Exception as exc:
        return _build_component(
            name="redis",
            ok=False,
            detail=f"redis unavailable: {exc}",
            critical=True,
        )


def _check_qdrant() -> dict:
    try:
        collection = get_qdrant_client().get_collection(QDRANT_COLLECTION_NAME)
        return _build_component(
            name="qdrant",
            ok=True,
            detail=(
                f"collection {QDRANT_COLLECTION_NAME} ready; "
                f"points={collection.points_count or 0}"
            ),
            critical=True,
        )
    except Exception as exc:
        return _build_component(
            name="qdrant",
            ok=False,
            detail=f"qdrant unavailable or collection missing: {exc}",
            critical=True,
        )


def _check_index_artifacts() -> dict:
    try:
        mysql_count = count_document_chunks()
        collection = get_qdrant_client().get_collection(QDRANT_COLLECTION_NAME)
        qdrant_count = int(collection.points_count or 0)
    except Exception as exc:
        return _build_component(
            name="index",
            ok=False,
            detail=f"index state unavailable: {exc}",
            critical=False,
        )
    ok = mysql_count > 0 and mysql_count == qdrant_count
    return _build_component(
        name="index",
        ok=ok,
        detail=(
            f"MySQL document_chunk={mysql_count}; "
            f"Qdrant points={qdrant_count}; mode=dense+sparse+rrf"
        ),
        critical=False,
    )


def _check_llm() -> dict:
    if is_llm_configured():
        return _build_component(
            name="llm",
            ok=True,
            detail="llm api key configured",
            critical=False,
        )
    return _build_component(
        name="llm",
        ok=False,
        detail="llm api key is not configured",
        critical=False,
    )


def _check_storage() -> dict:
    try:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        Path(INDEX_DIR).mkdir(parents=True, exist_ok=True)
        return _build_component(
            name="storage",
            ok=True,
            detail=f"storage directories ready: {RAW_DIR}, {INDEX_DIR}",
            critical=True,
        )
    except Exception as exc:
        return _build_component(
            name="storage",
            ok=False,
            detail=f"storage unavailable: {exc}",
            critical=True,
        )


def get_health_report() -> dict:
    components = [
        _check_storage(),
        _check_database(),
        _check_redis(),
        _check_qdrant(),
        _check_index_artifacts(),
        _check_llm(),
    ]

    critical_failures = [item for item in components if item["critical"] and not item["ok"]]
    non_critical_failures = [item for item in components if not item["critical"] and not item["ok"]]

    if critical_failures:
        status = "degraded"
    elif non_critical_failures:
        status = "warning"
    else:
        status = "ok"

    return {
        "status": status,
        "service": "rag-backend",
        "components": components,
    }
