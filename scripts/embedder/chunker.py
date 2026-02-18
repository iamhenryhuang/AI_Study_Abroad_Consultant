"""文字切片模組：使用 LangChain RecursiveCharacterTextSplitter。"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)


def chunk_text(text: str) -> list[str]:
    """將長文字切成多個 chunk，回傳 list[str]。"""
    if not text or not text.strip():
        return []
    return _splitter.split_text(text)
