from modelscope.hub.snapshot_download import snapshot_download

model_dir = snapshot_download(
    "BAAI/bge-reranker-base",
    local_dir=r"E:\models\bge-reranker-base",
)

print("downloaded to:", model_dir)