"""
RAG 評估模組 (RAG Triad)：評估檢索與生成的品質。
包含三個維度：
1. Context Relevance (脈絡相關性): 檢索到的內容是否與問題相關。
2. Faithfulness (忠實度/在地化): 回答是否完全根據檢索到的內容（無幻覺）。
3. Answer Relevance (回答相關性): 回答是否真正解決了使用者的問題。
"""
import os
import json
import re
from typing import List, Dict
from google import genai
from generator.gemini import get_gemini_client

def _parse_score(text: str) -> float:
    """從模型回傳的文字中提取分數 (1-5)。"""
    # 尋找 "Score: X" 或 "分數: X"
    match = re.search(r"(?:Score|分數):\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if match:
        try:
            score = float(match.group(1))
            return min(max(score, 1.0), 5.0)
        except ValueError:
            pass
    return 0.0

def evaluate_context_relevance(query: str, contexts: List[str]) -> Dict:
    """評估檢索內容與問題的相關性（嚴格模式）。"""
    client = get_gemini_client()
    context_combined = "\n\n".join([f"Context {i+1}: {c}" for i, c in enumerate(contexts)])
    
    prompt = f"""你是一位極其嚴苛的 RAG 系統質量稽核專家。請評估檢索內容對於回答問題的【專業充足度】。

使用者問題：{query}

檢索內容：
{context_combined}

評分標準（1-5）：
1: 完全不相關。
2: 僅有少數關鍵字對上，對於回答問題的核心毫無幫助。
3: 包含核心數據，但缺乏必要的上下文解釋，顯得資訊破碎。
4: 檢索質量高，能完全回答問題，但內容中混雜了一些無關的雜訊或冗餘段落。
5: 完美的檢索。每一行文字都與問題高度相關，無雜訊，且資訊深度足以支撐專業顧問的專業判斷。

請回傳以下格式：
Reasoning: (你的嚴格分析)
Score: (1-5 的分數)
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = response.text
        return {
            "metric": "Context Relevance",
            "reasoning": text.split("Score:")[0].replace("Reasoning:", "").strip(),
            "score": _parse_score(text)
        }
    except Exception as e:
        return {"metric": "Context Relevance", "error": str(e), "score": 0}

def evaluate_faithfulness(answer: str, contexts: List[str]) -> Dict:
    """評估回答是否忠於檢索內容（嚴格檢查有無過度推論）。"""
    client = get_gemini_client()
    context_combined = "\n\n".join([f"Context {i+1}: {c}" for i, c in enumerate(contexts)])
    
    prompt = f"""你是一位細節防範專家。請檢查「模型回答」是否【完全且僅限】基於「參考資料」。

參考資料：
{context_combined}

模型回答：
{answer}

評分標準（1-5）：
**嚴格判定：任何在參考資料中找不到明確來源的「推測性敘述」或「常識性補充」都應視為扣分項。**

1: 包含與原文矛盾的錯誤。
2: 大部分內容能對上，但在核心數據或具體要求上有編造跡象。
3: 文字基本忠誠，但加入了一些參考資料中並未提到的「自我推論」或外部知識。
4: 高度精準，僅在極其微小的語氣助詞或連接詞上帶有主觀色彩。
5: 絕對忠誠。回答中的每一個字、每一個論點、每一個數據在參考資料中都有明確的書面依據。

請回傳以下格式：
Reasoning: (你的詳細查核記錄)
Score: (1-5 的分數)
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = response.text
        return {
            "metric": "Faithfulness",
            "reasoning": text.split("Score:")[0].replace("Reasoning:", "").strip(),
            "score": _parse_score(text)
        }
    except Exception as e:
        return {"metric": "Faithfulness", "error": str(e), "score": 0}

def evaluate_answer_relevance(query: str, answer: str) -> Dict:
    """評估回答是否精煉且精準解決問題（嚴格檢查贅詞）。"""
    client = get_gemini_client()
    
    prompt = f"""你是一位溝通效率專家。請評估回答是否【最高效】地解決了使用者的問題。

使用者問題：{query}

模型回答：
{answer}

評分標準（1-5）：
1: 答非所問或語意模糊。
2: 回答太過冗長，混雜了過多使用者並未詢問的背景資訊（資訊過載）。
3: 回答正確但結構鬆散，核心答案被埋在段落中。
4: 清晰直接，結構良好，但仍可以更簡練。
5: 完美的回答。極其簡練、精準，直擊痛點，且沒有任何多餘的客套話或不相關資訊。

請回傳以下格式：
Reasoning: (你的效率分析)
Score: (1-5 的分數)
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = response.text
        return {
            "metric": "Answer Relevance",
            "reasoning": text.split("Score:")[0].replace("Reasoning:", "").strip(),
            "score": _parse_score(text)
        }
    except Exception as e:
        return {"metric": "Answer Relevance", "error": str(e), "score": 0}

def run_triad_evaluation(query: str, contexts: List[str], answer: str):
    """執行完整的 RAG Triad 評估並印出結果。"""
    print("\n" + "*"*20 + " RAG Triad 評估中 " + "*"*20)
    
    c_rel = evaluate_context_relevance(query, contexts)
    faith = evaluate_faithfulness(answer, contexts)
    a_rel = evaluate_answer_relevance(query, answer)
    
    results = [c_rel, faith, a_rel]
    
    for res in results:
        print(f"【{res['metric']}】 分數: {res['score']}/5")
        if 'reasoning' in res:
            print(f"  分析: {res['reasoning']}")
        if 'error' in res:
            print(f"  錯誤: {res['error']}")
        print("-" * 50)
    
    avg_score = sum(r['score'] for r in results) / 3
    print(f"### 平均 RAG Triad 得分: {avg_score:.2f} / 5.0")
    print("*" * 56 + "\n")
    
    return results
