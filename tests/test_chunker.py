# from pathlib import Path
# from app.loaders.document_loader import load_documents_from_directory
# from app.retrievers.chunker import chunk_documents
# #找到文件跟目录PROJECT_ROOT就是根目录resolve()就是转化为绝对路径
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# raw_dir = PROJECT_ROOT / "data" / "raw"
#
# documents = load_documents_from_directory(str(raw_dir))
# chunks = chunk_documents(documents, chunk_size=300)
#
# print(f"共生成 {len(chunks)} 个 chunks")
# for item in chunks[:5]:
#     print(item)
from pathlib import Path
from app.loaders.document_loader import load_documents_from_directory
from app.retrievers.chunker import chunk_documents

PROJECT_ROOT = Path(__file__).resolve().parents[1]
raw_dir = PROJECT_ROOT / "data" / "raw"

documents = load_documents_from_directory(str(raw_dir))
chunks = chunk_documents(documents, chunk_size=300, overlap=50)

print(f"共生成 {len(chunks)} 个 chunks")
for item in chunks[:5]:
    print(item)