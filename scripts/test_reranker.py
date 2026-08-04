from pathlib import Path

from sentence_transformers import CrossEncoder

from app.config import (
    RERANKER_LOCAL_FILES_ONLY,
    RERANKER_MODEL_NAME,
    USE_RERANKER,
)


def main() -> None:
    print(f"USE_RERANKER={USE_RERANKER}")
    print(f"RERANKER_MODEL_NAME={RERANKER_MODEL_NAME}")
    print(f"RERANKER_LOCAL_FILES_ONLY={RERANKER_LOCAL_FILES_ONLY}")

    model_path = Path(RERANKER_MODEL_NAME)
    print(f"model_path_exists={model_path.exists()}")

    if not model_path.exists():
        print(f"model path not found: {RERANKER_MODEL_NAME}")
        print("powershell -ExecutionPolicy Bypass -File scripts/download_reranker_model.ps1")
        return

    model = CrossEncoder(
        RERANKER_MODEL_NAME,
        local_files_only=RERANKER_LOCAL_FILES_ONLY,
    )
    scores = model.predict(
        [
            [
                "\u8ba4\u77e5\u8d1f\u8377\u662f\u4ec0\u4e48",
                "\u8ba4\u77e5\u8d1f\u8377\u662f\u4e2a\u4f53\u6267\u884c\u8ba4\u77e5\u4efb\u52a1\u65f6\u6d88\u8017\u7684\u8ba4\u77e5\u8d44\u6e90",
            ],
            [
                "What is cognitive load?",
                "Cognitive load refers to the mental effort used in working memory.",
            ],
        ]
    )
    print(f"rerank score 1={float(scores[0])}")
    print(f"rerank score 2={float(scores[1])}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(repr(exc))
        raise
