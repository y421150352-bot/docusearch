import re


CHINESE_CHAR_PATTERN = r"[\u4e00-\u9fff]"
CHINESE_PUNCTUATION = "，。！？；：、“”‘’（）《》【】"

# PDF table-of-contents pages commonly extract as
# "1.2 研究方法 ................. 57".  These are navigation artefacts, not
# document evidence, and otherwise receive an undeserved BM25 score.
TOC_DOT_LEADER_LINE = re.compile(
    r"(?m)^\s*[^\n]{0,240}?(?:\.{5,}|…{3,}|·{5,})\s*\d+\s*$"
)


def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")

    # Remove dotted page-number leaders before line breaks are normalized.
    text = TOC_DOT_LEADER_LINE.sub("\n", text)

    # Remove obvious metadata noise.
    text = re.sub(r"DOI[:：]?\s*\S+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"http[s]?://\S+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"www\.\S+", " ", text, flags=re.IGNORECASE)

    # Remove figure / table captions that frequently pollute PDF extraction.
    text = re.sub(r"图\s*\d+[^\n。！？；;]*", " ", text)
    text = re.sub(r"表\s*\d+[^\n。！？；;]*", " ", text)
    text = re.sub(r"Fig\.\s*\d+[^\n.!?;]*", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"Table\s*\d+[^\n.!?;]*", " ", text, flags=re.IGNORECASE)

    # Drop long reference sections when present.
    text = re.sub(r"参考文献[\s\S]*$", " ", text)
    text = re.sub(r"References[\s\S]*$", " ", text, flags=re.IGNORECASE)

    # Normalize whitespace while preserving paragraph intent.
    text = text.replace("\t", " ")
    text = re.sub(r"[ \u00a0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Fix abnormal spaces between Chinese characters.
    text = re.sub(
        rf"({CHINESE_CHAR_PATTERN})\s+({CHINESE_CHAR_PATTERN})",
        r"\1\2",
        text,
    )

    # Remove spaces around Chinese punctuation.
    text = re.sub(rf"\s+([{CHINESE_PUNCTUATION}])", r"\1", text)
    text = re.sub(rf"([{CHINESE_PUNCTUATION}])\s+", r"\1", text)

    # Normalize spaces around English punctuation a bit.
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,.;:!?])([A-Za-z])", r"\1 \2", text)

    # Collapse remaining whitespace.
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)

    return text.strip()
