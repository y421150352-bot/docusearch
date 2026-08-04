from app.loaders.document_loader import load_documents_from_directory


def test_load_documents_from_directory_reads_supported_files(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "notes.txt").write_text("第一份文档内容。", encoding="utf-8")
    (raw_dir / "summary.md").write_text("# 标题\n第二份文档内容。", encoding="utf-8")
    (raw_dir / "ignored.csv").write_text("id,value\n1,2\n", encoding="utf-8")

    documents = load_documents_from_directory(str(raw_dir))

    document_names = {item["document_name"] for item in documents}
    assert document_names == {"notes.txt", "summary.md"}
    assert all(item["page_number"] == 1 for item in documents)
