"""
rag_pipeline.py — RAG 完整流程（v2）

檢索 → 重排序 → 生成回答
或
Agentic RAG： Gemini Function Calling ReAct Loop

v2 改動：
  - 回傳結果包含 source_url，讓 Gemini 可以在回答中引用網頁來源
  - run_rag_pipeline 新增 school_id 參數，支援指定學校限定搜尋
"""

"""
rag_pipeline.py — RAG 完整流程（v2）

檢索 → 重排序 → 生成回答
或
Agentic RAG： Gemini Function Calling ReAct Loop
"""

import sys
import argparse
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from retriever.search import search_core, search_alternative
from retriever.multi_query import search_with_multi_query
from retriever.agent import run_agent
from generator.gemini import generate_admission_analysis

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from admission.admission_data import ADMISSION_DATA


def run_rag_pipeline(
    query: str,
    top_k: int = 7,
    use_multi_query: bool = False,
    school_id: str | None = None,
    profile: dict | None = None,
) -> bool:
    """
    執行完整的 RAG 流程：
    1. 檢索候選資料
    2. 將使用者 profile + school_stats + 檢索資料交給 LLM 判斷
    """

    print(f"\n開始執行 RAG 流程")
    print(f"   問題：'{query}'")

    if profile:
        print("\n使用者背景：")
        print(f"GPA   : {profile.get('gpa')}")
        print(f"GRE   : {profile.get('gre')}")
        print(f"TOEFL : {profile.get('toefl')}")
        print(f"Dream : {profile.get('dream_school')} - {profile.get('program')}")
        print(f"畢業學校: {profile.get('graduated_school', '未知')}")

    if school_id:
        print(f"過濾學校：{school_id}")

    # 1️⃣ 檢索候選資料
    if use_multi_query:
        print(f"  [RAG] 正在執行 Multi-Query 檢索...")
        results = search_with_multi_query(
            query, top_k=top_k, use_rerank=True, school_id=school_id
        )
    else:
        print(f"  [RAG] 正在檢索相關資料...")
        results = search_core(
            query, top_k=top_k, use_rerank=True, school_id=school_id
        )

    if not results:
        print("未能檢索到相關資訊。")
        return False

    print(f"  [RAG] 檢索到 {len(results)} 筆資料")

    # 2️⃣ 準備給 LLM 的 prompt
    profile_text = ""
    if profile:
        profile_text = f"""
        使用者資料：
        GPA: {profile.get('gpa')}
        GRE: {profile.get('gre')}
        TOEFL: {profile.get('toefl')}
        畢業學校: {profile.get('graduated_school', '未知')}
        目標學校/科系: {profile.get('dream_school')} / {profile.get('program')}
        """

    context_text = "\n".join([
        f"{d['university_name']} ({d.get('page_type', 'N/A')}) - {d.get('source_url', 'N/A')}\n{d['chunk_text'][:300]}..."
        for d in results
    ])

    # 3️⃣ 交給 LLM 判斷 Dream / Match / Safety
    answer = generate_admission_analysis(
        query=f"{profile_text}\n\n檢索資料:\n{context_text}\n\n問題:\n{query}",
        context_docs=results,
        profile=profile,
        school_stats=ADMISSION_DATA[{school_id}]
    )

    if answer:
        print("\n" + "=" * 30 + " Gemini 回答 " + "=" * 30)
        print(answer)
        print("=" * 73 + "\n")
        return True
    else:
        print("生成回答失敗。")
        return False


def run_agent_pipeline(
    query: str,
    max_steps: int = 5,
    verbose: bool = True,
) -> bool:
    """
    執行 Agentic RAG 流程（ReAct Loop）。
    """
    answer = run_agent(query, max_steps=max_steps, verbose=verbose)
    if answer:
        print("\n" + "=" * 30 + " Gemini Agent 回答 " + "=" * 30)
        print(answer)
        print("=" * 73 + "\n")
        return True
    else:
        print("生成回答失敗。")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="執行 RAG 流程")
    parser.add_argument("query", nargs="?", help="使用者問題")
    parser.add_argument("--agent", action="store_true", help="使用 Agentic RAG（ReAct Loop）")
    parser.add_argument("--max-steps", type=int, default=5, help="Agent 最大迭代次數")
    parser.add_argument("--multi-query", action="store_true", help="是否啟用 Multi-Query")
    parser.add_argument("--school", type=str, default=None, help="限定學校 e.g. cmu, caltech")
    parser.add_argument("--top-k", type=int, default=7, help="檢索數量")
    parser.add_argument("--gpa", type=float, help="GPA (e.g. 3.8)")
    parser.add_argument("--gre", type=int, help="GRE (e.g. 325)")
    parser.add_argument("--toefl", type=int, help="TOEFL (e.g. 105)")
    parser.add_argument("--dream-school", type=str, help="Dream school (e.g. MIT)")
    parser.add_argument("--program", type=str, help="Program (e.g. Computer Science)")
    parser.add_argument("--graduated-school", type=str, help="畢業學校 (e.g. 海本/南浙復上)")

    args = parser.parse_args()

    profile = None
    if args.gpa or args.gre or args.toefl:
        profile = {
            "gpa": args.gpa,
            "gre": args.gre,
            "toefl": args.toefl,
            "dream_school": args.dream_school,
            "program": args.program,
            "graduated_school": args.graduated_school,
        }

    q = args.query
    if not q:
        q = input("請輸入問題: ").strip()
        if q.endswith("--mq"):
            q = q.replace("--mq", "").strip()
            args.multi_query = True

    if q:
        if args.agent:
            run_agent_pipeline(q, max_steps=args.max_steps)
        else:
            run_rag_pipeline(
                q,
                top_k=args.top_k,
                use_multi_query=args.multi_query,
                school_id=args.school,
                profile=profile,
            )
    else:
        print("未輸入問題。")