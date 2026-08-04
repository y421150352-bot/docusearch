from app.loaders.text_cleaner import clean_text
from app.retrievers.indexer import is_noise_chunk


def test_dotted_table_of_contents_lines_are_removed():
    source = "目录\n第一章 绪论....................................57\n正文从这里开始。"
    cleaned = clean_text(source)

    assert "....................................57" not in cleaned
    assert "正文从这里开始" in cleaned


def test_table_of_contents_chunks_are_not_indexed():
    assert is_noise_chunk("目录\n第一章 绪论\n第二章 研究方法\n第三章 实验结果")
    assert not is_noise_chunk("本研究通过实验分析认知负荷在复杂任务环境中的变化，并报告了主要实验结果。")
