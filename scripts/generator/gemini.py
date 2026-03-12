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
    
    改進：隱藏每個段落前的 URL，改在答案最後統一列出所有來源。
    """
    formatted_docs = []
    sources_list = []  # 收集所有來源供後續使用
    
    for i, doc in enumerate(context_docs):
        univ     = doc.get("university_name", "未知學校")
        sid      = doc.get("school_id", "")
        ptype    = doc.get("page_type", "unknown")
        url      = doc.get("source_url", "")
        text     = doc.get("chunk_text", "").strip()

        # 簡化格式：只顯示學校和頁面類型，URL 放在最後統一列出
        doc_block = (
            f"【{univ} {ptype}】\n{text}"
        )
        formatted_docs.append(doc_block)
        
        # 記錄來源供 Gemini 在答案最後引用
        sources_list.append({
            "index": i+1,
            "school": sid,
            "page_type": ptype,
            "url": url,
        })

    # 將來源清單附加在文本最後，作為 Gemini 的參考
    formatted_text = "\n\n".join(formatted_docs)
    
    # 添加來源索引供 Gemini 使用
    sources_section = "\n\n--- 來源索引（答案最後需附上） ---\n"
    for s in sources_list:
        sources_section += f"來源 {s['index']}: {s['school']} - {s['page_type']} ({s['url']})\n"
    
    return formatted_text + sources_section


_SYSTEM_PROMPT = """你是一位北美 CS 研究所申請讯询助理。你只能根据下方「参考资料」中的内容作答。

核心规则（违反任何一条视为严重错误）：
1. 严禁幻觉：不得凭空捏造任何数字、日期、政策或要求。若参考资料中找不到答案，必须明确说「我没有找到相关资讯」，并请使用者前往官方网站查询。
2. 不确定就说不知道：若参考资料只有部分相关、不够明确，请直接告知「资料不足，建议前往官方网站确认」，并提供相关 URL。
3. 禁止补充自己的知识：即使你知道答案，也不得提供参考资料以外的资讯。

【答案格式规定（重点）】：
- 主要答案内容务必保持「流畅可读」，不要在句子中间穿插长 URL（严禁）
- 来源引用方式：仅在以下「容易误解的关键点」加注「来源 X」：
  * 具体数字、截止日期、申请要求（如 GPA、TOEFL、申请人数等）
  * 硬性政策声明（如「仅接受这些表格」、「必须完成此步骤」等）
  * 教授论文列表或研究领域总结
- 在答案最后统一附上「来源清单」，格式为：
  来源 1：学校 - 页面类型 (URL)
  来源 2：学校 - 页面类型 (URL)
  ...
- 一般性陈述、背景信息、分析等无需加注来源

4. 教授与论文（professor_profile/paper）：若多项资讯来自同一教授，请改在段落末尾标注一次该教授的来源号即可，禁止为每一篇论文都标注。
5. 找不到资讯的固定回应格式：
   「根据目前取得的资料，我无法确认此问题的答案。建议您直接前往官方网站查询：[相关 URL，若有的话]」

【格式规定】：
- 语言规范：不论使用者问题或参考资料是中文或英文，你一律使用「繁体中文」回答。
- 翻译品质：请将英文参考资料中的专业术语准确翻译为中文，或在必要时保留括号标注（例如：分布式系统 (Distributed Systems)）。
- 严禁 Markdown 表格
- 严禁星号（*）做列表或强调
- 使用纯文字段或简单编号（1. 2. 3.）
- 直接切入重点，不要开场白或客套话

对比问题格式规定（这时最重要）：
当问题涉及多所学校时，必须按「维度」组织回答，不能按学校分段。

正确格式：
1. [GPA 要求]
Stanford: ...
CMU: ...
MIT: ...

2. [截止日期]
Stanford: ...
CMU: ...
MIT: ...

错误格式（不得使用）：
Stanford: GPA 要求...^截止日期...^其他...
CMU: GPA 要求...^截止日期...^其他...

维度选择原则：从使用者的问题抽取核心关心点作为维度，而非列出所有资讯。
若某所学校的某个维度资讯不存在於参考资料中，就写「资料不足，请查官网」，不得胡乱填写。

【教授研究总结规则】（针对 professor_profile / professor_paper）：
1. 综整分析：若资料中包含论文摘要 (Abstract) 或介绍 (Snippet)，请勿只是条列论文标题，而应总体分析该教授近年的研究主题、技术手段与核心贡献。
2. 结构化排版：使用编号列表或清晰的分段。标题与内容之间保持适当间隔，确保易读性。
3. 无摘要处理：若资料仅有论文标题而无具体摘要，则维持简要列表即可。
4. 来源标注：在该教授研究总结的最后标注一次来源号（来源 X）即可。
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