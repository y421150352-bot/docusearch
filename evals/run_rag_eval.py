from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATASET_PATH = PROJECT_ROOT / "evals" / "rag_eval_dataset.jsonl"
EXPERIMENTS_DIR = PROJECT_ROOT / "evals" / "experiments"

try:
    import ragas  # noqa: F401

    RAGAS_AVAILABLE = True
except Exception:
    RAGAS_AVAILABLE = False


CHINESE_STOPWORDS = {
    "进行",
    "以及",
    "可以",
    "用于",
    "相关",
    "如果",
    "通常",
    "包括",
    "说明",
    "应当",
    "应说明",
    "方法",
    "数据",
    "结果",
    "研究",
    "文档",
    "文章",
    "回答",
    "内容",
    "主要",
    "提取",
    "评估",
    "指标",
    "特征",
    "分析",
    "通过",
    "问题",
    "系统",
}


def load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as file_object:
        for line_number, line in enumerate(file_object, start=1):
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            if not isinstance(record, dict):
                raise ValueError(f"invalid dataset row at line {line_number}")
            rows.append(record)
    return rows


def load_answer_question():
    from app.services.qa_service import answer_question

    return answer_question


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def sanitize_text(text: str) -> str:
    lowered = normalize_text(text).lower()
    lowered = re.sub(r"[^\w\u4e00-\u9fff]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _cjk_keyword_candidates(text: str) -> list[str]:
    normalized = sanitize_text(text)
    candidates: list[str] = []
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
        max_size = min(4, len(sequence))
        for size in range(max_size, 1, -1):
            for start in range(0, len(sequence) - size + 1):
                token = sequence[start : start + size]
                if token in CHINESE_STOPWORDS:
                    continue
                candidates.append(token)
    return candidates


def extract_keywords(text: str) -> list[str]:
    normalized = sanitize_text(text)
    latin_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{1,}", normalized)
    candidates = _cjk_keyword_candidates(normalized) + latin_tokens

    keywords: list[str] = []
    seen: set[str] = set()
    for token in candidates:
        token = token.strip()
        if len(token) < 2:
            continue
        if token in CHINESE_STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)

    return keywords[:20]


def get_expected_keywords(sample: dict[str, Any], ground_truth: str) -> list[str]:
    expected_keywords = sample.get("expected_keywords")
    if isinstance(expected_keywords, list):
        normalized_keywords: list[str] = []
        seen: set[str] = set()
        for item in expected_keywords:
            keyword = normalize_text(item).lower()
            if len(keyword) < 2 or keyword in seen:
                continue
            seen.add(keyword)
            normalized_keywords.append(keyword)
        if normalized_keywords:
            return normalized_keywords
    return extract_keywords(ground_truth)


def summarize_retrieval_types(retrieval_types: list[str]) -> dict[str, int]:
    counter = Counter(item for item in retrieval_types if item)
    return dict(counter)


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def to_jsonable_sources(sources: list[Any]) -> list[dict[str, Any]]:
    normalized_sources: list[dict[str, Any]] = []
    for source in sources:
        if hasattr(source, "model_dump"):
            normalized_sources.append(source.model_dump())
        elif isinstance(source, dict):
            normalized_sources.append(source)
        else:
            normalized_sources.append(
                {
                    "document_name": getattr(source, "document_name", None),
                    "page_number": getattr(source, "page_number", None),
                    "quote": getattr(source, "quote", ""),
                    "score": getattr(source, "score", None),
                    "rerank_score": getattr(source, "rerank_score", None),
                    "retrieval_type": getattr(source, "retrieval_type", None),
                }
            )
    return normalized_sources


def to_jsonable_key_points(key_points: list[Any]) -> list[dict[str, Any]]:
    normalized_key_points: list[dict[str, Any]] = []
    for item in key_points:
        if hasattr(item, "model_dump"):
            normalized_key_points.append(item.model_dump())
        elif isinstance(item, dict):
            normalized_key_points.append(item)
        else:
            normalized_key_points.append(
                {
                    "title": getattr(item, "title", ""),
                    "content": getattr(item, "content", ""),
                }
            )
    return normalized_key_points


def compute_keyword_overlap_score(answer: str, keywords: list[str]) -> tuple[float, list[str], list[str]]:
    normalized_answer = sanitize_text(answer)
    if not keywords:
        return 0.0, [], []

    matched_keywords = [keyword for keyword in keywords if keyword in normalized_answer]
    missing_keywords = [keyword for keyword in keywords if keyword not in normalized_answer]
    score = len(matched_keywords) / len(keywords)
    return clamp_score(score), matched_keywords, missing_keywords


def compute_source_quality_score(sources: list[dict[str, Any]]) -> tuple[float, float]:
    if not sources:
        return 0.0, 0.0

    source_count = len(sources)
    count_score = 1.0 if source_count >= 3 else 0.7 if source_count == 2 else 0.4

    quote_lengths = [len(normalize_text(source.get("quote"))) for source in sources if normalize_text(source.get("quote"))]
    avg_quote_length = average([float(length) for length in quote_lengths]) if quote_lengths else 0.0

    if avg_quote_length >= 40 and avg_quote_length <= 220:
        quote_score = 1.0
    elif avg_quote_length >= 20 and avg_quote_length < 40:
        quote_score = 0.7
    elif avg_quote_length > 220 and avg_quote_length <= 320:
        quote_score = 0.8
    elif avg_quote_length > 0:
        quote_score = 0.4
    else:
        quote_score = 0.0

    return clamp_score(count_score * 0.7 + quote_score * 0.3), avg_quote_length


def compute_answer_completeness_score(answer_length: int) -> float:
    if answer_length <= 0:
        return 0.0
    if answer_length < 50:
        return 0.1
    if answer_length < 100:
        return 0.3
    if answer_length < 200:
        return 0.6
    if answer_length <= 800:
        return 1.0
    if answer_length <= 1200:
        return 0.85
    return 0.7


def evaluate_sample(
    sample: dict[str, Any],
    answer_question_func,
) -> dict[str, Any]:
    question = normalize_text(sample.get("question"))
    ground_truth = normalize_text(sample.get("ground_truth"))
    document_name = sample.get("document_name")
    tags = sample.get("tags") or []
    expected_keywords = get_expected_keywords(sample, ground_truth)

    started_at = time.perf_counter()
    response = answer_question_func(
        question=question,
        document_name=document_name,
        use_cache=False,
        persist_cache=False,
        persist_history=False,
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

    answer = normalize_text(getattr(response, "summary", ""))
    key_points = to_jsonable_key_points(getattr(response, "key_points", []))
    sources = to_jsonable_sources(getattr(response, "sources", []))

    retrieval_types = [
        normalize_text(source.get("retrieval_type"))
        for source in sources
        if source.get("retrieval_type") is not None
    ]
    rerank_scores = [
        float(source["rerank_score"])
        for source in sources
        if source.get("rerank_score") is not None
    ]

    keyword_overlap_score, matched_keywords, missing_keywords = compute_keyword_overlap_score(
        answer,
        expected_keywords,
    )
    source_quality_score, avg_source_quote_length = compute_source_quality_score(sources)
    answer_completeness_score = compute_answer_completeness_score(len(answer))
    final_lightweight_score = clamp_score(
        keyword_overlap_score * 0.4
        + source_quality_score * 0.3
        + answer_completeness_score * 0.3
    )

    return {
        "question": question,
        "ground_truth": ground_truth,
        "expected_keywords": expected_keywords,
        "answer": answer,
        "summary": answer,
        "key_points": key_points,
        "document_name": document_name,
        "tags": tags,
        "sources": sources,
        "source_count": len(sources),
        "retrieval_types": retrieval_types,
        "retrieval_type_summary": summarize_retrieval_types(retrieval_types),
        "rerank_scores": rerank_scores,
        "latency_ms": latency_ms,
        "answer_length": len(answer),
        "has_sources": len(sources) > 0,
        "avg_source_quote_length": avg_source_quote_length,
        "keyword_overlap_score": keyword_overlap_score,
        "source_quality_score": source_quality_score,
        "answer_completeness_score": answer_completeness_score,
        "final_lightweight_score": final_lightweight_score,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "error": None,
    }


def build_error_result(
    sample: dict[str, Any],
    error_message: str,
) -> dict[str, Any]:
    question = normalize_text(sample.get("question"))
    ground_truth = normalize_text(sample.get("ground_truth"))
    document_name = sample.get("document_name")
    tags = sample.get("tags") or []
    expected_keywords = get_expected_keywords(sample, ground_truth)
    return {
        "question": question,
        "ground_truth": ground_truth,
        "expected_keywords": expected_keywords,
        "answer": "",
        "summary": "",
        "key_points": [],
        "document_name": document_name,
        "tags": tags,
        "sources": [],
        "source_count": 0,
        "retrieval_types": [],
        "retrieval_type_summary": {},
        "rerank_scores": [],
        "latency_ms": 0.0,
        "answer_length": 0,
        "has_sources": False,
        "avg_source_quote_length": 0.0,
        "keyword_overlap_score": 0.0,
        "source_quality_score": 0.0,
        "answer_completeness_score": 0.0,
        "final_lightweight_score": 0.0,
        "matched_keywords": [],
        "missing_keywords": expected_keywords,
        "error": error_message,
    }


def write_csv(results: list[dict[str, Any]], output_path: Path) -> None:
    fieldnames = [
        "question",
        "ground_truth",
        "expected_keywords",
        "document_name",
        "tags",
        "summary",
        "answer_length",
        "source_count",
        "has_sources",
        "avg_source_quote_length",
        "keyword_overlap_score",
        "source_quality_score",
        "answer_completeness_score",
        "final_lightweight_score",
        "matched_keywords",
        "missing_keywords",
        "retrieval_types",
        "retrieval_type_summary",
        "rerank_scores",
        "latency_ms",
        "error",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file_object:
        writer = csv.DictWriter(file_object, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "question": item["question"],
                    "ground_truth": item["ground_truth"],
                    "expected_keywords": json.dumps(item["expected_keywords"], ensure_ascii=False),
                    "document_name": item["document_name"],
                    "tags": json.dumps(item["tags"], ensure_ascii=False),
                    "summary": item["summary"],
                    "answer_length": item["answer_length"],
                    "source_count": item["source_count"],
                    "has_sources": item["has_sources"],
                    "avg_source_quote_length": item["avg_source_quote_length"],
                    "keyword_overlap_score": item["keyword_overlap_score"],
                    "source_quality_score": item["source_quality_score"],
                    "answer_completeness_score": item["answer_completeness_score"],
                    "final_lightweight_score": item["final_lightweight_score"],
                    "matched_keywords": json.dumps(item["matched_keywords"], ensure_ascii=False),
                    "missing_keywords": json.dumps(item["missing_keywords"], ensure_ascii=False),
                    "retrieval_types": json.dumps(item["retrieval_types"], ensure_ascii=False),
                    "retrieval_type_summary": json.dumps(
                        item["retrieval_type_summary"],
                        ensure_ascii=False,
                    ),
                    "rerank_scores": json.dumps(item["rerank_scores"], ensure_ascii=False),
                    "latency_ms": item["latency_ms"],
                    "error": item["error"],
                }
            )


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    successes = [item for item in results if not item["error"]]
    failures = [item for item in results if item["error"]]
    return {
        "total": total,
        "success_count": len(successes),
        "failed_count": len(failures),
        "avg_latency_ms": average([float(item["latency_ms"]) for item in successes]),
        "avg_answer_length": average([float(item["answer_length"]) for item in successes]),
        "avg_source_count": average([float(item["source_count"]) for item in successes]),
        "has_sources_rate": round(
            (sum(1 for item in successes if item["has_sources"]) / len(successes)) if successes else 0.0,
            4,
        ),
        "avg_final_lightweight_score": average(
            [float(item["final_lightweight_score"]) for item in successes]
        ),
        "avg_keyword_overlap_score": average(
            [float(item["keyword_overlap_score"]) for item in successes]
        ),
        "avg_source_quality_score": average(
            [float(item["source_quality_score"]) for item in successes]
        ),
        "avg_answer_completeness_score": average(
            [float(item["answer_completeness_score"]) for item in successes]
        ),
    }


def main() -> int:
    if not RAGAS_AVAILABLE:
        print("Ragas not installed, skip advanced ragas metrics.")

    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        dataset = load_dataset(DATASET_PATH)
    except Exception as exc:
        print(f"Failed to load dataset: {exc!r}")
        return 1

    import_error: str | None = None
    answer_question_func = None
    try:
        answer_question_func = load_answer_question()
    except Exception as exc:
        import_error = (
            "Failed to import app.services.qa_service.answer_question. "
            "Please check FastAPI/MySQL/Redis/Qdrant/LLM dependencies. "
            f"detail={exc!r}"
        )
        print(import_error)

    results: list[dict[str, Any]] = []
    for sample in dataset:
        try:
            if import_error:
                raise RuntimeError(import_error)
            results.append(evaluate_sample(sample, answer_question_func))
        except Exception as exc:
            error_message = repr(exc)
            print(f"[EVAL ERROR] question={sample.get('question')} error={error_message}")
            results.append(build_error_result(sample, error_message))

    summary = build_summary(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = EXPERIMENTS_DIR / f"rag_eval_{timestamp}.csv"
    json_path = EXPERIMENTS_DIR / f"rag_eval_{timestamp}.json"

    write_csv(results, csv_path)
    with json_path.open("w", encoding="utf-8") as file_object:
        json.dump(
            {
                "summary": summary,
                "results": results,
                "ragas_available": RAGAS_AVAILABLE,
            },
            file_object,
            ensure_ascii=False,
            indent=2,
        )

    print("RAG Evaluation Summary")
    print(f"total: {summary['total']}")
    print(f"success_count: {summary['success_count']}")
    print(f"failed_count: {summary['failed_count']}")
    print(f"avg_latency_ms: {summary['avg_latency_ms']}")
    print(f"avg_answer_length: {summary['avg_answer_length']}")
    print(f"avg_source_count: {summary['avg_source_count']}")
    print(f"has_sources_rate: {summary['has_sources_rate']}")
    print(f"avg_final_lightweight_score: {summary['avg_final_lightweight_score']}")
    print(f"avg_keyword_overlap_score: {summary['avg_keyword_overlap_score']}")
    print(f"avg_source_quality_score: {summary['avg_source_quality_score']}")
    print(f"avg_answer_completeness_score: {summary['avg_answer_completeness_score']}")
    print(f"csv: {csv_path}")
    print(f"json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
