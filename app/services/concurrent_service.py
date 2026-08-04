from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_parallel_tasks(
    tasks: list[Callable[[], object]],
    max_workers: int = 4,
) -> list[dict]:
    if not tasks:
        return []

    max_worker_count = max(1, min(max_workers, len(tasks)))
    results: list[dict | None] = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=max_worker_count) as executor:
        future_to_index = {
            executor.submit(task): index
            for index, task in enumerate(tasks)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = {
                    "success": True,
                    "result": future.result(),
                }
            except Exception as exc:
                results[index] = {
                    "success": False,
                    "error": str(exc),
                }

    return [item or {"success": False, "error": "task returned no result"} for item in results]
