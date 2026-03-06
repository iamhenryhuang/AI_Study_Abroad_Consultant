"""
eval_runner.py — 整合式 RAG 評估腳本
======================================
直接呼叫專案的 search_core() 與 generate_answer()，
對預定義的 Ground Truth 資料集跑四項指標：
  - Recall@k
  - Context Precision  (RAGAS 版)
  - Context Recall
  - F1 Score           (token-level, 中英文混合)

使用方法（從專案根目錄執行）:
    python scripts/evaluator/eval_runner.py
    python scripts/evaluator/eval_runner.py --top-k 7 --k 5 --no-gen

資料集格式說明:
    EVAL_DATASET 中每一筆為一個 dict，包含：
      query          (str)       : 使用者問題
      relevant_urls  (list[str]) : GT 相關頁面的 source_url（從 DB 取得）
      ground_truth   (str)       : 標準參考答案（用於 F1 計算）
      school_id      (str|None)  : 限定學校（None = 全庫搜尋）

注意事項:
    relevant_urls 是以 source_url 作為文件 ID。
    請根據你 DB 中實際存在的 URL 填寫，可用以下 SQL 查詢參考:
        SELECT DISTINCT source_url FROM document_chunks WHERE school_id = 'cmu';
"""

from __future__ import annotations

import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime

# ── 路徑設定 ──────────────────────────────────────────────────────────
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from retriever.search import search_core
from generator.gemini import generate_answer
from evaluator.evaluator import RAGEvaluator, evaluate_batch


# ══════════════════════════════════════════════════════════════════════
# Ground Truth 資料集（根據你的資料庫 URL 填入）
# ══════════════════════════════════════════════════════════════════════
#
# 說明：
#   relevant_urls → 應包含能回答該問題的頁面 source_url，
#                   可能是一個或多個（例如 CMU admissions 頁 + FAQ 頁）。
#   ground_truth  → 用於 F1 評估，寫出關鍵答案即可，不需完整句子。
#
EVAL_DATASET = [
    # ── CMU ───────────────────────────────────────────────────────────
    {
        "query": "What are the application deadlines for CMU SCS graduate programs?",
        "relevant_urls": [
            "https://www.cs.cmu.edu/academics/graduate-admissions",
        ],
        "ground_truth": (
            "CMU SCS early deadline is November 19 2025 and final deadline is December 10 2025. "
            "MHCI final deadline is January 15 2026."
        ),
        "school_id": "cmu",
    },
    {
        "query": "What English proficiency tests does CMU SCS accept?",
        "relevant_urls": [
            "https://www.cs.cmu.edu/academics/graduate-admissions",
        ],
        "ground_truth": (
            "CMU SCS accepts TOEFL iBT, IELTS, and Duolingo. "
            "A successful applicant typically scores at least 100 on TOEFL iBT. "
            "An IELTS score of 7 is equivalent to a TOEFL score of 100."
        ),
        "school_id": "cmu",
    },
    {
        "query": "How many letters of recommendation are required for CMU SCS graduate applications?",
        "relevant_urls": [
            "https://www.cs.cmu.edu/academics/graduate-admissions",
        ],
        "ground_truth": (
            "CMU SCS requires three letters of recommendation. "
            "Applicants may submit up to five letters."
        ),
        "school_id": "cmu",
    },

    # ── Stanford ───────────────────────────────────────────────────────
    {
        "query": "What are the PhD admissions requirements for Stanford CS?",
        "relevant_urls": [
            "https://www.cs.stanford.edu/admissions/phd-admissions",
            "https://www.cs.stanford.edu/admissions/phd-admissions-frequently-asked-questions",
        ],
        "ground_truth": (
            "Stanford CS PhD applicants need strong academic preparation in CS fundamentals, "
            "research experience, letters of recommendation, statement of purpose, and transcripts."
        ),
        "school_id": "stanford",
    },
    {
        "query": "What are the Stanford CS master's degree application deadlines?",
        "relevant_urls": [
            "https://www.cs.stanford.edu/admissions-graduate-application-deadlines",
            "https://www.cs.stanford.edu/admissions-all-application-deadlines",
            "https://www.cs.stanford.edu/admissions/masters-admissions",
        ],
        "ground_truth": (
            "Stanford CS master's application deadlines vary by program. "
            "Refer to the official deadlines page for specific dates."
        ),
        "school_id": "stanford",
    },
    {
        "query": "What documents are required for the Stanford CS graduate application checklist?",
        "relevant_urls": [
            "https://www.cs.stanford.edu/admissions/graduate-application-checklists",
        ],
        "ground_truth": (
            "Stanford CS graduate application requires transcripts, letters of recommendation, "
            "statement of purpose, CV, and application fee."
        ),
        "school_id": "stanford",
    },

    # ── MIT ────────────────────────────────────────────────────────────
    {
        "query": "How do I apply to the MIT CSE PhD program?",
        "relevant_urls": [
            "https://cse.mit.edu/programs-admissions/apply",
            "https://cse.mit.edu/programs-admissions/cse-phd-program",
        ],
        "ground_truth": (
            "MIT CSE PhD application requires completing the graduate online application, "
            "submitting transcripts, letters of recommendation, and statement of objectives."
        ),
        "school_id": "mit",
    },
    {
        "query": "What are the frequently asked questions about MIT CSE admissions?",
        "relevant_urls": [
            "https://cse.mit.edu/programs-admissions/apply/admissions-faqs",
        ],
        "ground_truth": (
            "MIT CSE admissions FAQs cover topics such as eligibility, required documents, "
            "GRE requirements, and the timeline for decisions."
        ),
        "school_id": "mit",
    },

    # ── Caltech ────────────────────────────────────────────────────────
    {
        "query": "What is the Caltech graduate admissions checklist?",
        "relevant_urls": [
            "https://www.gradoffice.caltech.edu/admissions/checklist",
            "https://www.gradoffice.caltech.edu/admissions",
        ],
        "ground_truth": (
            "Caltech graduate admissions checklist includes application form, transcripts, "
            "letters of recommendation, statement of purpose, and test scores."
        ),
        "school_id": "caltech",
    },
    {
        "query": "What are the frequently asked questions for Caltech graduate applicants?",
        "relevant_urls": [
            "https://www.gradoffice.caltech.edu/admissions/faq-applicants",
        ],
        "ground_truth": (
            "Caltech admissions FAQ addresses questions about GRE requirements, "
            "application fees, international student requirements, and financial support."
        ),
        "school_id": "caltech",
    },

    # ── UCLA ────────────────────────────────────────────────────────────
    {
        "query": "What are the graduate admission requirements for UCLA CS?",
        "relevant_urls": [
            "https://www.cs.ucla.edu/graduate-admissions",
            "https://www.cs.ucla.edu/graduate-admission-frequently-asked-questions",
        ],
        "ground_truth": (
            "UCLA CS graduate admissions requires a bachelor's degree in CS or related field, "
            "transcripts, letters of recommendation, statement of purpose, and GRE scores."
        ),
        "school_id": "ucla",
    },
    {
        "query": "What are the graduate degree requirements for UCLA CS students?",
        "relevant_urls": [
            "https://www.cs.ucla.edu/graduate-requirements",
        ],
        "ground_truth": (
            "UCLA CS graduate degree requirements include completing required coursework, "
            "passing qualifying exams, and submitting a thesis or dissertation."
        ),
        "school_id": "ucla",
    },
]


# ══════════════════════════════════════════════════════════════════════
# 評估流程
# ══════════════════════════════════════════════════════════════════════

def run_evaluation(
    top_k: int = 5,
    k_for_recall: int = 3,
    use_rerank: bool = True,
    run_generation: bool = True,
) -> dict:
    """
    對 EVAL_DATASET 執行完整評估，回傳各指標的詳細結果與平均分。

    Args:
        top_k:          向量搜尋回傳的總文件數。
        k_for_recall:   Recall@k 中的 k 值（應 <= top_k）。
        use_rerank:     是否啟用 CrossEncoder 重排序。
        run_generation: 是否執行生成並計算 F1（需連線 Gemini API）。

    Returns:
        包含 per_query 結果與 aggregate 平均分的 dict。
    """
    ev = RAGEvaluator()
    per_query_results = []

    print(f"\n{'='*65}")
    print(f"  RAG 評估開始  |  top_k={top_k}  Recall@{k_for_recall}  rerank={use_rerank}")
    print(f"{'='*65}")

    # 過濾掉 relevant_urls 未填寫的 query（視為草稿）
    active_dataset = [q for q in EVAL_DATASET if q.get("relevant_urls")]
    skipped = len(EVAL_DATASET) - len(active_dataset)

    if skipped:
        print(f"  [注意] 有 {skipped} 筆 query 尚未填入 relevant_urls，已略過。")
        print(f"         請確認 DB 中的 source_url 並填入 EVAL_DATASET。\n")

    if not active_dataset:
        print("  [錯誤] EVAL_DATASET 中沒有任何已設定 relevant_urls 的 query。")
        print("         請先填入 relevant_urls 再執行評估。")
        return {}

    for i, item in enumerate(active_dataset, 1):
        query       = item["query"]
        relevant    = item["relevant_urls"]
        gt_answer   = item["ground_truth"]
        school_id   = item.get("school_id")

        print(f"\n[{i}/{len(active_dataset)}] {query}")
        print(f"  學校過濾 : {school_id or '全庫'} | GT 文件數: {len(relevant)}")

        # ── 1. 向量檢索 ──────────────────────────────────────────────
        t0 = time.time()
        results = search_core(
            query,
            top_k=top_k,
            use_rerank=use_rerank,
            school_id=school_id,
        )
        latency_search = time.time() - t0

        if not results:
            print("  [搜尋] 未找到任何結果，跳過此 query。")
            per_query_results.append({
                "query": query,
                "retrieved_urls": [],
                "relevant_urls": relevant,
                "recall_at_k": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0,
                "f1_score": 0.0,
                "prediction": "",
                "ground_truth": gt_answer,
                "search_latency_s": latency_search,
                "gen_latency_s": 0.0,
            })
            continue

        # 取出 source_url 作為 doc ID（依排名順序）
        retrieved_urls = [r.get("source_url", "") for r in results]

        # ── 2. 計算檢索指標 ──────────────────────────────────────────
        recall   = ev.recall_at_k(retrieved_urls, relevant, k=k_for_recall)
        ctx_prec = ev.context_precision(retrieved_urls, relevant)
        ctx_rec  = ev.context_recall(retrieved_urls, relevant)

        print(f"  [檢索] {len(results)} 筆結果 ({latency_search:.2f}s)")
        print(f"  Recall@{k_for_recall}: {recall:.4f}  "
              f"CtxPrec: {ctx_prec:.4f}  CtxRec: {ctx_rec:.4f}")

        # ── 3. 生成回答 + F1 ─────────────────────────────────────────
        f1        = 0.0
        pred_ans  = ""
        gen_lat   = 0.0

        if run_generation:
            t1 = time.time()
            pred_ans = generate_answer(query, results) or ""
            gen_lat  = time.time() - t1
            f1       = ev.f1_score(pred_ans, gt_answer)
            print(f"  [生成] 完成 ({gen_lat:.2f}s)  F1: {f1:.4f}")
        else:
            print("  [生成] 已略過（--no-gen）")

        # ── 印出命中/未命中的 URL ──────────────────────────────────
        relevant_set = set(relevant)
        hits = [u for u in retrieved_urls if u in relevant_set]
        misses = [u for u in relevant if u not in set(retrieved_urls)]

        if hits:
            print(f"  命中 URL ({len(hits)}):")
            for u in hits:
                print(f"    + {u}")
        if misses:
            print(f"  未命中 GT URL ({len(misses)}):")
            for u in misses:
                print(f"    - {u}")

        per_query_results.append({
            "query":              query,
            "retrieved_urls":     retrieved_urls,
            "relevant_urls":      relevant,
            "recall_at_k":        recall,
            "context_precision":  ctx_prec,
            "context_recall":     ctx_rec,
            "f1_score":           f1,
            "prediction":         pred_ans,
            "ground_truth":       gt_answer,
            "search_latency_s":   latency_search,
            "gen_latency_s":      gen_lat,
        })

    # ── 4. 聚合計算平均分 ─────────────────────────────────────────────
    n = len(per_query_results)
    if n == 0:
        return {"per_query": [], "aggregate": {}}

    def avg(key):
        return sum(r[key] for r in per_query_results) / n

    aggregate = {
        f"recall_at_{k_for_recall}":    avg("recall_at_k"),
        "context_precision":             avg("context_precision"),
        "context_recall":                avg("context_recall"),
        "f1_score":                      avg("f1_score") if run_generation else None,
        "avg_search_latency_s":          avg("search_latency_s"),
        "avg_gen_latency_s":             avg("gen_latency_s") if run_generation else None,
        "num_queries":                   n,
    }

    # ── 5. 列印彙整結果 ───────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  評估完成 ({n} 筆 query)")
    print(f"{'='*65}")
    print(f"  Recall@{k_for_recall}         : {aggregate[f'recall_at_{k_for_recall}']:.4f}")
    print(f"  Context Precision    : {aggregate['context_precision']:.4f}")
    print(f"  Context Recall       : {aggregate['context_recall']:.4f}")
    if run_generation:
        print(f"  F1 Score (avg)       : {aggregate['f1_score']:.4f}")
    print(f"  Avg 搜尋耗時         : {aggregate['avg_search_latency_s']:.2f}s")
    if run_generation:
        print(f"  Avg 生成耗時         : {aggregate['avg_gen_latency_s']:.2f}s")
    print(f"{'='*65}\n")

    return {
        "evaluated_at":  datetime.now().isoformat(),
        "config": {
            "top_k": top_k,
            "k_for_recall": k_for_recall,
            "use_rerank": use_rerank,
            "run_generation": run_generation,
        },
        "aggregate":  aggregate,
        "per_query":  per_query_results,
    }


# ══════════════════════════════════════════════════════════════════════
# CLI 入口點
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="對專案 RAG pipeline 執行評估，計算 Recall@k / Context Precision / Context Recall / F1"
    )
    parser.add_argument(
        "--top-k", type=int, default=5,
        help="向量搜尋回傳文件數（預設 5）"
    )
    parser.add_argument(
        "--k", type=int, default=3,
        help="Recall@k 中的 k（預設 3，必須 <= top-k）"
    )
    parser.add_argument(
        "--no-rerank", action="store_true",
        help="關閉 CrossEncoder 重排序"
    )
    parser.add_argument(
        "--no-gen", action="store_true",
        help="跳過 Gemini 生成步驟（只評估檢索，速度更快）"
    )
    parser.add_argument(
        "--save", type=str, default=None, metavar="PATH",
        help="將詳細結果儲存為 JSON 檔案（e.g. --save results.json）"
    )
    args = parser.parse_args()

    if args.k > args.top_k:
        parser.error(f"--k ({args.k}) 不得大於 --top-k ({args.top_k})")

    results = run_evaluation(
        top_k=args.top_k,
        k_for_recall=args.k,
        use_rerank=not args.no_rerank,
        run_generation=not args.no_gen,
    )

    if results and args.save:
        save_path = Path(args.save)
        save_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"詳細結果已儲存至：{save_path.resolve()}")


if __name__ == "__main__":
    main()
