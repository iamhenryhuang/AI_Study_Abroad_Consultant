"""
chunker.py — 智慧分段模組（v2）

根據頁面類型動態選擇 chunk size，以適配不同長度的官方網頁文字。

頁面類型判斷依據 URL 路徑關鍵詞：
  - faq / frequently-asked  → chunk_size=1200（FAQ 問答通常較長，切太小反而失去上下文）
  - checklist / requirements → chunk_size=600   （條列式資訊，中等大小）
  - admissions / apply      → chunk_size=800    （申請說明段落，中等大小）
  - 其他 / 預設             → chunk_size=700

overlap 固定為 chunk_size * 0.1（10%）以確保上下文連貫。
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

# 頁面類型對應的 chunk_size（字元數）
_PAGE_TYPE_SIZES: dict[str, int] = {
    "faq":          1200,
    "checklist":     600,
    "requirements":  600,
    "admissions":    800,
    "apply":         800,
    "accepting":     700,
    "general":       700,
}

_DEFAULT_CHUNK_SIZE = 700
_SEPARATORS = ["\n\n", "\n", "。", ".", " ", ""]


def infer_page_type(url: str) -> str:
    """
    從 URL 路徑推斷頁面類型。
    回傳 page_type 字串，例如 'faq', 'admissions', 'general'。
    """
    url_lower = url.lower()
    if "faq" in url_lower or "frequently-asked" in url_lower:
        return "faq"
    if "checklist" in url_lower or "requirements" in url_lower:
        return "checklist"
    if "admissions" in url_lower or "graduate-admissions" in url_lower:
        return "admissions"
    if "apply" in url_lower:
        return "apply"
    if "accepting" in url_lower or "acceptance" in url_lower:
        return "accepting"
    return "general"


def _make_splitter(page_type: str) -> RecursiveCharacterTextSplitter:
    """根據 page_type 建立對應的 splitter。"""
    size = _PAGE_TYPE_SIZES.get(page_type, _DEFAULT_CHUNK_SIZE)
    overlap = max(50, int(size * 0.1))
    return RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=_SEPARATORS,
    )


def chunk_text(text: str, page_type: str = "general") -> list[str]:
    """
    將長文字依 page_type 切成多個 chunk，回傳 list[str]。

    Args:
        text:      原始純文字（爬取自網頁）
        page_type: 頁面類型，影響 chunk 大小

    Returns:
        切分後的字串列表，過濾掉空白 chunk。
    """
    if not text or not text.strip():
        return []
    splitter = _make_splitter(page_type)
    chunks = splitter.split_text(text.strip())
    # 過濾掉純空白或非常短的 chunk（< 30 字元）
    return [c for c in chunks if len(c.strip()) >= 30]
