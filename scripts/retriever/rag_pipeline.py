"""
RAG 完整流程：檢索 -> 重排序 -> 生成回答 -> (可選) 評估。
"""
import sys
import argparse
from pathlib import Path

# 讓 scripts 目錄在 path 中
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from retriever.search import search_core
from retriever.multi_query import search_with_multi_query
from generator.gemini import generate_answer
from evaluator.rag_evaluation import run_triad_evaluation

def run_rag_pipeline(query: str, top_k: int = 3, evaluate: bool = False, use_multi_query: bool = False):
    """
    執行完整的 RAG 流程。
    Args:
        query: 使用者提出的問題。
        top_k: 檢索的數量。
        evaluate: 是否啟用 RAG Triad 評估。
        use_multi_query: 是否使用 Multi-Query 擴展查詢。
    """
    print(f"\n開始執行 RAG 流程，問題：'{query}'")
    
    # 1. 檢索與重排序
    if use_multi_query:
        print(f"  [RAG] 正在執行 Multi-Query 檢索...")
        results = search_with_multi_query(query, top_k=top_k, use_rerank=True)
    else:
        print(f"  [RAG] 正在檢索相關資料...")
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
        
        # 3. 執行評估 (RAG Triad)
        if evaluate:
            from generator.gemini import format_context_for_prompt
            # 傳遞完整的、包含 Metadata 的格式化內容
            formatted_contexts = [format_context_for_prompt([res]) for res in results]
            run_triad_evaluation(query, formatted_contexts, answer)
            
        return True
    else:
        print("生成回答失敗。")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="執行 RAG 流程")
    parser.add_argument("query", nargs="?", help="使用者問題")
    parser.add_argument("--eval", action="store_true", help="是否執行 RAG Triad 評估")
    parser.add_argument("--multi-query", action="store_true", help="是否啟用 Multi-Query")
    args = parser.parse_args()
    
    q = args.query
    if not q:
        q = input("請輸入問題以執行 RAG 檢索生成 (輸入 '--eval' 結尾可開啟評估, '--mq' 可開啟 Multi-Query): ").strip()
        if q.endswith("--eval"):
            q = q.replace("--eval", "").strip()
            args.eval = True
        if q.endswith("--mq"):
            q = q.replace("--mq", "").strip()
            args.multi_query = True
    
    if q:
        run_rag_pipeline(q, evaluate=args.eval, use_multi_query=args.multi_query)
    else:
        print("未輸入問題。")
