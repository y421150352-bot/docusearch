# RAG Evaluation

This directory is used for offline RAG evaluation.

`rag_eval_dataset.jsonl` is the fixed test dataset. Each line is a JSON object with:

- `question`
- `ground_truth`
- `document_name`
- `tags`

`run_rag_eval.py` calls the existing RAG system and saves evaluation results.

Current lightweight metrics:

- `answer_length`
- `source_count`
- `has_sources`
- `avg_source_quote_length`
- `contains_ground_truth_keywords`
- `retrieval_type_summary`
- `error`

Advanced metrics can be added later with Ragas, including:

- `faithfulness`
- `response_relevancy`
- `context_precision`
- `context_recall`

If Ragas is not installed, the script will skip advanced metrics and continue running.

Run:

```powershell
& "E:\实习项目\.venv\Scripts\python.exe" evals\run_rag_eval.py
```

Syntax check:

```powershell
& "E:\实习项目\.venv\Scripts\python.exe" -m py_compile evals\run_rag_eval.py
```

Results:

- `evals/experiments/*.csv`
- `evals/experiments/*.json`

Each run writes a timestamped CSV and JSON file for later comparison.
