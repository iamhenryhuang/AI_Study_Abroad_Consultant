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
from retriever.reranker import rerank

def search_core(query: str, top_k: int = 3, use_rerank: bool = True) -> list[dict]:
    """執行檢索核心邏輯，回傳文件列表。"""
    # 1. 向量化問題
    query_embeddings = embed_texts([query])
    if not query_embeddings:
        return []
    query_vector = query_embeddings[0]

    # 2. 連線資料庫
    conn = get_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            # 3. 執行向量相似度搜尋 (初篩)
            initial_k = 15 if use_rerank else top_k
            
            cur.execute("""
                SELECT 
                    dc.chunk_text, 
                    dc.metadata,
                    dc.source,
                    u.university,
                    u.program,
                    1 - (dc.embedding <=> %s::vector) AS vector_score
                FROM document_chunks dc
                JOIN universities u ON dc.university_id = u.id
                ORDER BY dc.embedding <=> %s::vector
                LIMIT %s;
            """, (query_vector, query_vector, initial_k))
            
            colnames = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            if not rows:
                return []

            candidates = [dict(zip(colnames, row)) for row in rows]

            # 4. 重排序 (精篩)
            if use_rerank:
                results = rerank(query, candidates, top_n=top_k)
            else:
                results = candidates[:top_k]
            
            return results
            
    except Exception as e:
        print(f"搜尋核心出錯: {e}")
        return []
    finally:
        conn.close()

def run_search(query: str, top_k: int = 3, use_rerank: bool = True):
    """執行向量搜尋（可選重排序）並印出結果。"""
    print(f"\n正在檢索問題: '{query}'")
    print(f"  [1/2] 正在執行向量搜尋與重排序...")
    
    results = search_core(query, top_k=top_k, use_rerank=use_rerank)
    
    if not results:
        print("查無相關資料。")
        return True

    print(f"  [2/2] 檢索完成，結果如下：\n")
    print("=" * 80)
    
    for i, res in enumerate(results, 1):
        score_str = f"向量分數: {res['vector_score']:.4f}"
        if 'rerank_score' in res:
            score_str += f", Re-rank 分數: {res['rerank_score']:.4f}"
        
        output = (
            f"【結果 {i}】 {score_str}\n"
            f"學校: {res['university']}\n"
            f"學系: {res['program']}\n"
            f"來源: {res.get('source', 'unknown')}\n"
            f"摘要: {res['chunk_text'].strip()[:600]}...\n"
        )
        
        meta = res.get('metadata')
        if meta:
            output += "--- 結構化資訊 ---\n"
            output += f"  - GPA 最低要求: {meta.get('minimum_gpa', 'N/A')}\n"
            output += f"  - TOEFL 最低要求: {meta.get('toefl_min', 'N/A')}\n"
            output += f"  - GRE 狀態: {meta.get('gre_status', 'N/A')}\n"
            output += f"  - 截止日期: {meta.get('fall_deadline', 'N/A')}\n"
        output += "-" * 80 + "\n"
        print(output)
    
    return True

if __name__ == "__main__":
    test_query = "UIUC MSCS GPA and TOEFL requirements?"
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    run_search(test_query)
