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
    
    # 組合 context，同時包含 chunk_text 與 結構化 metadata
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
            f"--- 來源 {i+1} ({univ} / {prog}) ---\n"
            f"[結構化資訊] {meta_text}\n"
            f"[詳細描述] {text}"
        )
        formatted_docs.append(doc_block)

    context_text = "\n\n".join(formatted_docs)
    
    prompt = f"""你是一位專業的北美 CS 留學顧問，擅長分析各校官網數據並提供量身定制的申請策略。
請根據提供的【參考資料】（包含學校硬性指標與背景描述）來回答使用者問題。

### 核心規則：
1. **數據精確性**：GPA、TOEFL、IELTS、GRE、截止日期等數據必須嚴格遵循參考資料，不得隨意估算或編造。
2. **語義深度整合**：請利用參考資料中的「詳細描述」，解釋該校的「研究風氣」、「就業趨勢」或「地理優勢」。
3. **誠實原則**：若資料中缺少特定資訊，請回答「目前的資料庫中暫無此細節」，並引導使用者參考官方連結。
4. **專業口吻**：語氣應專業、誠懇，適時以「建議」或「提醒」的方式與使用者對話。

### 輸出格式規範（Markdown）：
- **## 快速診斷**：簡短回答使用者的核心問題。
- **### 顧問深度解析**：結合資料中的描述，提供具體的申請優勢或備註（例如：強調研究能力、實習機會等）。

### 限制：
- 僅使用繁體中文回答。
- 嚴禁提及你是 AI 模型或任何關於資料庫檢索的技術術語。

--- 參考資料 ---
{context_text}

--- 使用者問題 ---
{query}

請提供詳細且有條理的回答：
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"[Gemini] 生成回答時發生錯誤: {e}")
        return None
