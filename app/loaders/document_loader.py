from pathlib import Path
from app.loaders.text_cleaner import clean_text
import pymupdf


def _ensure_file_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if not path.is_file():
        raise ValueError(f"这不是一个有效文件: {path}")


def _read_text(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        raise ValueError(f"文件编码不是 utf-8，暂时无法读取: {path.name}")


def load_txt(file_path: str) -> list[dict]:
    path = Path(file_path)
    _ensure_file_exists(path)
    content = clean_text(_read_text(path))

    if not content:
        return []

    return [
        {
            "document_name": path.name,
            "page_number": 1,
            "content": content
        }
    ]


def load_md(file_path: str) -> list[dict]:
    path = Path(file_path)
    _ensure_file_exists(path)
    content = clean_text(_read_text(path))

    if not content:
        return []

    return [
        {
            "document_name": path.name,
            "page_number": 1,
            "content": content
        }
    ]


def load_pdf(file_path: str) -> list[dict]:
    #将字符串路径转换成 Path 对象，方便后面直接用 .name 获取文件名。
    path = Path(file_path)
    _ensure_file_exists(path)

    results = []
    #使用 pymupdf 库打开这个 PDF 文件。此时 doc 就像一本已经翻开的书，停留在内存里。
    doc = pymupdf.open(file_path)

    try:
        #enumerate(doc, start=1)它在翻页的同时，自动给你一个页码计数器。
        # start=1 表示我们从第 1 页开始数（而不是程序员习惯的第 0 页），这个数字会存进 page_index。
        for page_index, page in enumerate(doc, start=1):
            #get_text()：把当前这一页可见的文字全部“抠”出来。
            text = clean_text(page.get_text())

            if not text:
                continue

            results.append(
                {
                    "document_name": path.name,
                    "page_number": page_index,
                    "content": text
                }
            )
    finally:
        doc.close()

    return results


def load_document(file_path: str) -> list[dict]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return load_txt(file_path)
    elif suffix == ".md":
        return load_md(file_path)
    elif suffix == ".pdf":
        return load_pdf(file_path)
    else:
        raise ValueError(f"暂不支持的文件类型: {suffix}")
def load_documents_from_directory(directory_path: str) -> list[dict]:
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")
    if not directory.is_dir():
        raise ValueError(f"这不是一个有效目录: {directory}")

    supported_suffixes = {".txt", ".md", ".pdf"}
    all_results = []

    for path in directory.iterdir():#表示遍历这个目录下的内容
        if path.is_file() and path.suffix.lower() in supported_suffixes:
            document_results = load_document(str(path))
            all_results.extend(document_results)

    return all_results
