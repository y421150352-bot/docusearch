from app.retrievers import indexer


def test_build_and_load_index_from_directory(tmp_path, monkeypatch) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "demo.txt").write_text(
        "认知负荷评估用于飞行训练。认知负荷评估结合主观量表与生理信号。" * 4,
        encoding="utf-8",
    )

    captured: list[dict] = []
    monkeypatch.setattr(
        indexer,
        "replace_document_chunks",
        lambda chunks: captured.extend(chunks) or len(chunks),
    )

    count = indexer.build_index_from_directory(
        str(raw_dir),
        chunk_size=80,
        overlap=1,
    )

    assert count == len(captured)
    assert captured
    assert captured[0]["document_name"] == "demo.txt"
