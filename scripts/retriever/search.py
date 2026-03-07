#!/usr/bin/env python3
"""
檢索模組：將問題轉成向量，並從 pgvector 中尋找最相關的 chunk。
"""
import os
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中
# 假設此檔案位於 scripts/retriever/search.py
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
ROOT_DIR = SCRIPTS_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db.connection import get_connection
from embedder.vectorize import embed_texts

<<<<<<< Updated upstream
def run_search(query: str, top_k: int = 3):
    """執行向量搜尋並印出結果。"""
    print(f"\n正在檢索問題: '{query}'")
    
    # 1. 向量化問題
    print("  [1/3] 正在將問題轉為向量...")
=======
def search_alternative(
    dream_dept: str,
    top_k: int = 5,
) -> list[dict]:
    """
    搜尋備案科系 / 學校

    Args:
        dream_dept: 夢想科系 (e.g. "Computer Science")
        top_k:      回傳筆數

    Returns:
        list[dict]
    """

    if not dream_dept:
        return []

    # 1️⃣ 建立多個查詢（提高 recall）
    queries = [
        f"{dream_dept} program",
        f"{dream_dept} graduate program",
        f"universities with strong {dream_dept}",
        f"top universities for {dream_dept}",
    ]

    all_results = []
    seen_urls = set()

    for q in queries:
        results = search_core(
            q,
            top_k=top_k,
            use_rerank=True
        )

        for r in results:
            url = r.get("source_url")

            # 避免重複資料
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)

    # 2️⃣ 依 vector_score 排序
    all_results.sort(
        key=lambda x: x.get("vector_score", 0),
        reverse=True
    )

    # 3️⃣ 回傳前 top_k
    return all_results[:top_k]

def search_core(
    query: str,
    top_k: int = 5,
    use_rerank: bool = True,
    school_id: str | None = None,
    page_type: str | None = None,
) -> list[dict]:
    """
    執行向量檢索，回傳文件列表。

    Args:
        query:      使用者查詢字串
        top_k:      最終返回筆數
        use_rerank: 是否啟用 Cross-Encoder 重排序
        school_id:  若指定則只搜尋該學校（e.g. 'cmu'）
        page_type:  若指定則只搜尋該類型頁面（e.g. 'faq'）

    Returns:
        list of dict，每個 dict 包含：
          - chunk_text
          - source_url
          - page_type
          - university_name
          - school_id
          - vector_score
          - rerank_score (若 use_rerank=True)
          - metadata (JSONB)
    """
    # 1. 向量化查詢
>>>>>>> Stashed changes
    query_embeddings = embed_texts([query])
    if not query_embeddings:
        print("向量化失敗。")
        return
    query_vector = query_embeddings[0]

    # 2. 連線資料庫
    conn = get_connection()
    if not conn:
        print("無法連線至資料庫。")
        return

    try:
        with conn.cursor() as cur:
            # 3. 執行向量相似度搜尋
            print(f"  [2/3] 正在 pgvector 中搜尋最接近的 {top_k} 個結果...")
            cur.execute("""
                SELECT 
                    dc.chunk_text, 
                    dc.metadata,
                    u.university,
                    u.program,
                    1 - (dc.embedding <=> %s::vector) AS similarity
                FROM document_chunks dc
                JOIN universities u ON dc.university_id = u.id
                ORDER BY dc.embedding <=> %s::vector
                LIMIT %s;
            """, (query_vector, query_vector, top_k))
            
            rows = cur.fetchall()
            
            print(f"  [3/3] 搜尋完成，結果如下：\n")
            print("=" * 80)
            
            if not rows:
                print("查無相關資料。")
                return True
            else:
                for i, (text, meta, univ, prog, score) in enumerate(rows, 1):
                    res = (
                        f"【結果 {i}】 相似度: {score:.4f}\n"
                        f"學校: {univ}\n"
                        f"學系: {prog}\n"
                        f"摘要: {text.strip()[:600]}...\n"
                    )
                    if meta:
                        res += "--- 結構化資訊 ---\n"
                        res += f"  - GPA 最低要求: {meta.get('minimum_gpa', 'N/A')}\n"
                        res += f"  - TOEFL 最低要求: {meta.get('toefl_min', 'N/A')}\n"
                        res += f"  - GRE 狀態: {meta.get('gre_status', 'N/A')}\n"
                        res += f"  - 截止日期: {meta.get('fall_deadline', 'N/A')}\n"
                    res += "-" * 80 + "\n"
                    print(res)
                return True
            
    except Exception as e:
        print(f"搜尋出錯: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    test_query = "UIUC MSCS GPA and TOEFL requirements?"
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    run_search(test_query)
