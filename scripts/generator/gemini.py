"""
gemini.py — Gemini 2.5 Flash 回答生成模組（v2）

System prompt 核心原則：
  - 嚴格依賴提供的 context，不得自行腦補
  - 若 context 不足以回答，明確說不知道並引導使用者查官網
  - 輸出格式：繁體中文、純文字、無星號
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

_client = None


def get_gemini_client():
    """取得 Gemini GenAI Client。"""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("未在 .env 中找到 GOOGLE_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client


def format_context_for_prompt(context_docs: list[dict]) -> str:
    """
    將檢索到的文件列表格式化為 LLM 易讀的字串（v2 schema）。

    每筆 doc 包含：
      - chunk_text     : 段落文字
      - university_name: 學校全名
      - school_id      : 學校識別碼
      - page_type      : 頁面類型（admissions / faq / checklist…）
      - source_url     : 原始頁面 URL
      - metadata       : JSONB（school_id, page_type, source_url）
    """
    formatted_docs = []
    for i, doc in enumerate(context_docs):
        univ     = doc.get("university_name", "未知學校")
        sid      = doc.get("school_id", "")
        ptype    = doc.get("page_type", "unknown")
        url      = doc.get("source_url", "")
        text     = doc.get("chunk_text", "").strip()

        doc_block = (
            f"--- 來源 {i+1} [{univ} ({sid})] 頁面類型：{ptype} ---\n"
            f"原始 URL：{url}\n"
            f"{text}"
        )
        formatted_docs.append(doc_block)

    return "\n\n".join(formatted_docs)


_SYSTEM_PROMPT = """你是一位北美 CS 研究所申請談詢助理。你只能根據下方「參考資料」中的內容作答。

核心規則（違反任何一條視為嚴重錯誤）：
1. 嚴禁幻覺：不得憑空捽造任何數字、日期、政策或要求。若參考資料中找不到答案，必須明確說「我沒有找到相關資訊」，並請使用者前往官方網站查詢。
2. 不確定就說不知道：若參考資料只有部分相關、不夠明確，請直接告知「資料不足，建議前往官方網站確認」，並提供 source_url。
3. 禁止補充自己的知識：即使你知道答案，也不得提供參考資料以外的資訊。
4. 引用來源：回答中若有具體數據，請在句末標註（來源：[page_type] URL）。
5. 找不到資訊的固定回應格式：
   「根據目前取得的資料，我無法確認此問題的答案。建議您直接前往官方網站查詢：[相關 URL，若有的話]」

格式規定：
- 語言：繁體中文
- 嚴禁 Markdown 表格
- 嚴禁星號（*）做列表或強調
- 使用純文字段或簡單編號（1. 2. 3.）
- 直接切入重點，不要開場白或客套話

對比問題格式規定（這時最重要）：
當問題涉及多所學校時，必須按「維度」組織回答，不能按學校分段。

正確格式：
1. [GPA 要求]
Stanford: ...
CMU: ...
MIT: ...

2. [截止日期]
Stanford: ...
CMU: ...
MIT: ...

錯誤格式（不得使用）：
Stanford: GPA 要求...^截止日期...^其他...
CMU: GPA 要求...^截止日期...^其他...

維度選擇原則：從使用者的問題抽取核心關心點作為維度，而非列出所有資訊。
若某所學校的某個維度資訊不存在於參考資料中，就寫「資料不足，請查官網」，不得胡亂填寫。
"""


def generate_answer(
    query: str,
    context_docs: list[dict],
    model_name: str = "gemini-2.5-flash",
) -> str | None:
    """
    根據檢索到的文件生成回答。

    Args:
        query:        使用者問題
        context_docs: 檢索並排序後的文件清單（v2 schema）
        model_name:   模型名稱

    Returns:
        回答字串，或 None（API 呼叫失敗時）
    """
    client = get_gemini_client()

    context_text = format_context_for_prompt(context_docs)

    prompt = f"""{_SYSTEM_PROMPT}

--- 參考資料（共 {len(context_docs)} 筆） ---
{context_text}

--- 使用者問題 ---
{query}

--- 你的回答 ---
（請嚴格遵守以上規則，若資料不足請直接說不知道並引導查官網）
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        # 清除殘留星號
        clean_text = response.text.replace("*", "")
        return clean_text
    except Exception as e:
        print(f"[Gemini] 生成回答時發生錯誤: {e}")
        return None
