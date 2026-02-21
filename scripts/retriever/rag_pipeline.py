"""
RAG 完整流程：檢索 -> 重排序 -> 生成回答。
"""
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from retriever.search import run_search
from generator.gemini import generate_answer

def run_rag_pipeline(query: str, top_k: int = 3):
    """
    執行完整的 RAG 流程。
    """
    print(f"\n開始執行 RAG 流程，問題：'{query}'")
    
    # 1. 檢索與重排序
    # 我們需要稍微修改 search.py 的 run_search，或在這裡直接調用其核心邏輯
    # 為了保持 search.py 的獨立性，我們這裡可以考慮重構或直接獲取其結果
    
    # 注意：目前的 run_search 只會印出結果並回傳 True/False。
    # 我需要一個能回傳 results 的版本。
    
    # 暫時解決方案：我們直接在 search.py 裡面加一個回傳結果的 version，
    # 或者我們在這裡重新實現一下流程。
    
    # 這裡我先調用我即將重構後的 search_core 函數
    from retriever.search import search_core
    
    results = search_core(query, top_k=top_k, use_rerank=True)
    
    if not results:
        print("未能檢索到相關資訊。")
        return False
        
    # 2. 生成回答
    print(f"  [RAG] 正在使用 Gemini 2.5 Flash 生成回答...")
    answer = generate_answer(query, results)
    
    if answer:
        print("\n" + "="*30 + " Gemini 回答 " + "="*30)
        print(answer)
        print("="*73 + "\n")
        return True
    else:
        print("生成回答失敗。")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = input("請輸入問題以執行 RAG 檢索生成: ").strip()
    
    if q:
        run_rag_pipeline(q)
    else:
        print("未輸入問題。")
