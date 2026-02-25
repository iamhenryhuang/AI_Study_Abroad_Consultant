"""
Gemini 模型生成模組：封裝與 Google Gemini 2.5 Flash 的互動。
"""
import os
from dotenv import load_dotenv
from google import genai

# 載入環境變數
load_dotenv()

_client = None

def get_gemini_client():
    """取得 Gemini GenAI Client"""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("未在 .env 中找到 GOOGLE_API_KEY")
        _client = genai.Client(api_key=api_key)
    return _client

def generate_answer(query: str, context_docs: list[dict], model_name: str = "gemini-2.5-flash"):
    """
    根據檢索到的文件生成回答。
    
    Args:
        query: 使用者問題
        context_docs: 檢索並排序後的文件清單
        model_name: 模型名稱
    """
    client = get_gemini_client()
    
def format_context_for_prompt(context_docs: list[dict]) -> str:
    """將檢索到的原始文件列表格式化為 LLM 易讀的字串。"""
    formatted_docs = []
    for i, doc in enumerate(context_docs):
        univ = doc.get('university', '未知大學')
        prog = doc.get('program', '未知系所')
        text = doc.get('chunk_text', '')
        meta = doc.get('metadata', {})
        
        # 將 metadata 轉為可讀文字
        meta_parts = []
        if meta:
            if meta.get('fall_deadline'): meta_parts.append(f"秋季截止日: {meta['fall_deadline']}")
            if meta.get('spring_deadline'): meta_parts.append(f"春季截止日: {meta['spring_deadline']}")
            if meta.get('minimum_gpa'): meta_parts.append(f"GPA 要求: {meta['minimum_gpa']}")
            if meta.get('toefl_min'): 
                req_str = " (必備)" if meta.get('toefl_required') else ""
                meta_parts.append(f"TOEFL 要求: {meta['toefl_min']}{req_str}")
            if meta.get('ielts_min'): 
                req_str = " (必備)" if meta.get('ielts_required') else ""
                meta_parts.append(f"IELTS 要求: {meta['ielts_min']}{req_str}")
            if meta.get('gre_status'): meta_parts.append(f"GRE 狀態: {meta['gre_status']}")
            if meta.get('recommendation_letters'): meta_parts.append(f"推薦信需求: {meta['recommendation_letters']} 封")
            if meta.get('interview_required'): meta_parts.append(f"面試需求: {meta['interview_required']}")
        
        meta_text = " | ".join(meta_parts) if meta_parts else "無結構化資訊"
        
        doc_block = (
            f"--- 來源 {i+1} ({univ} / {prog} / 來源: {doc.get('source', 'official')}) ---\n"
            f"[結構化資訊] {meta_text}\n"
            f"[詳細描述] {text}"
        )
        formatted_docs.append(doc_block)

    return "\n\n".join(formatted_docs)

def generate_answer(query: str, context_docs: list[dict], model_name: str = "gemini-2.5-flash"):
    """
    根據檢索到的文件生成回答。
    
    Args:
        query: 使用者問題
        context_docs: 檢索並排序後的文件清單
        model_name: 模型名稱
    """
    client = get_gemini_client()
    
    # 組合 context，同時包含 chunk_text 與 結構化 metadata
    context_text = format_context_for_prompt(context_docs)
    
    prompt = f"""角色：北美 CS 申請專家，需結合官方數據與社群實戰經驗回答。

規則：
1. 內容至上：直接切入重點，嚴禁任何開場白、客套話或重複內容。
2. 禁表格與特殊符號：嚴禁使用 Markdown 表格結構。嚴禁使用星號（*）作為列表或強調符號。
3. 純文字整理：請使用純文字段落或簡單的編號（如 1. 2. 3.）進行資訊整理。
4. 視覺清爽：僅在必要時區分段落，保持版面極簡，不要有過多的 Markdown 標記。
5. 來源識別：區分官方來源與 Reddit 經驗，直接在文字中註明「官方：」或「社群：」。
6. 語言：繁體中文。

--- 參考資料 ---
{context_text}

--- 使用者問題 ---
{query}

輸出要求：
1. 按學校區分重點，使用簡單的文字描述。
2. 錄取門檻與實戰案例合併在敘事中，直接說重點。
3. 嚴禁出現任何星號（*）字符。
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        # 額外清理：確保輸出中完全沒有星號
        clean_text = response.text.replace("*", "")
        return clean_text
    except Exception as e:
        print(f"[Gemini] 生成回答時發生錯誤: {e}")
        return None
