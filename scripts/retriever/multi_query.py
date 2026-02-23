"""
Multi-Query 模組：利用 LLM 將單一問題擴展為多個相關問題，以提高檢索召回率。
"""
import os
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from generator.gemini import get_gemini_client
from retriever.search import search_core
from retriever.reranker import rerank

def generate_multi_queries(query: str, n: int = 3) -> list[str]:
    """
    使用 Gemini 生成多個相關問題。
    """
    client = get_gemini_client()
    
    prompt = f"""你是一個搜尋引擎優化專家。使用者的原始問題是："{query}"。
請產生 {n} 個相關但措辭稍有不同的搜尋查詢，目的是從向量資料庫中檢索出更全面的資訊。
這些查詢應該涵蓋問題的不同層面，或者使用不同的專業術語（例如同時包含全稱與縮寫）。

請直接條列式輸出查詢，每行一個，不要有數字編號或任何前言。
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        # 處理輸出的文字，分割並過濾空行
        queries = [q.strip() for q in response.text.split('\n') if q.strip()]
        # 確保包含原始問題
        if query not in queries:
            queries.insert(0, query)
        return queries[:n+1]
    except Exception as e:
        print(f"[Multi-Query] 生成查詢時出錯: {e}")
        return [query]

def search_with_multi_query(query: str, top_k: int = 3, use_rerank: bool = True) -> list[dict]:
    """
    執行 Multi-Query 檢索流程。
    """
    # 1. 生成多個問題
    multi_queries = generate_multi_queries(query)
    print(f"  [Multi-Query] 生成的問題：{multi_queries}")
    
    # 2. 對每個問題執行檢索
    all_results = []
    seen_chunks = set() # 用於去重，以 chunk_text 為 key
    
    for q in multi_queries:
        # 這裡 use_rerank 先設為 False，因為我們最後會統一重排序
        results = search_core(q, top_k=top_k * 2, use_rerank=False)
        for res in results:
            chunk_key = res['chunk_text']
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                all_results.append(res)
    
    # 3. 統一執行重排序（由 LLM 決定哪 3 個最適合原本的問題）
    if use_rerank and all_results:
        print(f"  [Multi-Query] 正在對 {len(all_results)} 個候選結果進行重排序...")
        final_results = rerank(query, all_results, top_n=top_k)
    else:
        # 如果不重排序，就根據原始向量分數排序並取 top_k
        all_results.sort(key=lambda x: x.get('vector_score', 0), reverse=True)
        final_results = all_results[:top_k]
        
    return final_results

if __name__ == "__main__":
    test_q = "UIUC MSCS requirement"
    res = search_with_multi_query(test_q)
    for i, r in enumerate(res):
        print(f"{i+1}. {r['university']} - {r['program']} (Score: {r.get('vector_score')})")
