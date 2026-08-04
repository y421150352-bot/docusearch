# If the hf command does not exist, run:
# Install huggingface_hub first with the project's .venv interpreter.
# This downloads the bilingual reranker model into E:\models\bge-reranker-base.

$env:HF_ENDPOINT = "https://hf-mirror.com"
hf download BAAI/bge-reranker-base --local-dir E:\models\bge-reranker-base
