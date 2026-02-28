"""
chunker.py — 智慧分段模組（v3）

根據頁面類型動態選擇 chunk size，並對 FAQ 頁面做預處理，
以防止問答對話被橫向截斷。

頁面類型對應策略：
  - faq / frequently-asked  → 先用 regex 拆出每個 Q&A pair，各自作為一個 chunk
                               若單個 Q&A 超過 2000 字元才再切分
  - checklist / requirements → chunk_size=1200（條列式英文，需保留完整條目）
  - admissions / apply      → chunk_size=1600（申請說明段落）
  - reddit                  → chunk_size=900（口語短段落，來源為 Reddit 貼文）
  - 其他 / 預設             → chunk_size=1400

overlap 固定為 chunk_size * 0.2（20%），最少 150 字元，
以確保英文長句在邊界處有足夠的上下文重疊。
"""

from __future__ import annotations

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── 頁面類型對應的 chunk_size（字元數）──────────────────────────────
# 原始資料為英文，平均每個單字約 5–6 字元 + 空格
# chunk_size=1400 ≈ 200–250 個英文單字（約 2–3 個段落）
_PAGE_TYPE_SIZES: dict[str, int] = {
    "faq":          2000,   # FAQ 個別問答若超過此長度才二次切分
    "checklist":    1200,   # 條列式資訊，保留完整條目
    "requirements": 1200,
    "admissions":   1600,   # 申請說明段落
    "apply":        1600,
    "accepting":    1400,
    "reddit":        900,   # Reddit 口語短段落
    "general":      1400,
}

_DEFAULT_CHUNK_SIZE = 1400
_MIN_OVERLAP = 150          # 英文最少 overlap 字元數
_SEPARATORS = ["\n\n", "\n", ". ", "。", " ", ""]


# ── FAQ 專用預處理 ──────────────────────────────────────────────────

# 匹配 "Do you...?" / "What is...?" / "If I...?" / "Can I...?" 等常見問句開頭
_FAQ_SPLIT_RE = re.compile(
    r"(?<=[.?!])\s*(?="          # 在句號/問號/驚嘆號後
    r"(?:Do|Does|Is|Are|Can|Will|Should|How|What|Where|When|Why|Who|"
    r"Which|If|Am|Was|Were|Has|Have|Had|Would|Could|May|Must|Shall)\s)",
    re.MULTILINE,
)


def _split_faq_pairs(text: str) -> list[str]:
    """
    嘗試將 FAQ 頁面拆成獨立的 Q&A pair。

    策略：
      1. 先用問句開頭的 regex 分割，找出候選邊界
      2. 合併過短的碎片（< 80 字元）到前一個 pair
      3. 若單個 pair 超過 FAQ chunk_size 上限，再用通用 splitter 二次切分
    """
    faq_chunk_size = _PAGE_TYPE_SIZES["faq"]
    raw_pairs = _FAQ_SPLIT_RE.split(text)

    pairs: list[str] = []
    buffer = ""
    for part in raw_pairs:
        part = part.strip()
        if not part:
            continue
        # 合併太短的碎片（可能是被誤切的連接短句）
        if len(part) < 80:
            buffer = (buffer + " " + part).strip()
        else:
            if buffer:
                pairs.append(buffer)
            buffer = part
    if buffer:
        pairs.append(buffer)

    # 若單個 pair 仍太長，二次切分
    fallback_splitter = _make_splitter("faq", secondary=True)
    result: list[str] = []
    for pair in pairs:
        if len(pair) > faq_chunk_size:
            result.extend(fallback_splitter.split_text(pair))
        else:
            result.append(pair)

    return result


# ── 核心工具函式 ────────────────────────────────────────────────────

def infer_page_type(url: str) -> str:
    """
    從 URL 路徑推斷頁面類型。

    回傳 page_type 字串，例如 'faq', 'admissions', 'general'。
    Reddit 資料通常由 pipeline 直接傳入 page_type='reddit'，
    此處的 URL 判斷作為備用。
    """
    url_lower = url.lower()
    if "reddit.com" in url_lower:
        return "reddit"
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


def _make_splitter(page_type: str, secondary: bool = False) -> RecursiveCharacterTextSplitter:
    """
    根據 page_type 建立對應的 splitter。

    secondary=True 時用於 FAQ 二次切分，採用固定大小而不遞迴推斷。
    """
    size = _PAGE_TYPE_SIZES.get(page_type, _DEFAULT_CHUNK_SIZE)
    overlap = max(_MIN_OVERLAP, int(size * 0.20))
    return RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=_SEPARATORS,
    )


def chunk_text(text: str, page_type: str = "general") -> list[str]:
    """
    將長文字依 page_type 切成多個 chunk，回傳 list[str]。

    Args:
        text:      原始純文字（爬取自網頁或 Reddit）
        page_type: 頁面類型，影響 chunk 策略與大小

    Returns:
        切分後的字串列表，過濾掉空白或過短的 chunk（< 60 字元）。

    特殊處理：
        - page_type == 'faq'：先用 regex 拆出 Q&A pairs，再切分
        - 其他：直接用 RecursiveCharacterTextSplitter
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    if page_type == "faq":
        chunks = _split_faq_pairs(text)
    else:
        splitter = _make_splitter(page_type)
        chunks = splitter.split_text(text)

    # 過濾過短 chunk（英文 60 字元 ≈ 8–12 個單字，已是最短有意義句子）
    return [c for c in chunks if len(c.strip()) >= 60]
