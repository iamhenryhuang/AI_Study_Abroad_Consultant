"""
run_fetch.py — 教授 Google Scholar 資料抓取 CLI 入口

功能：
  1. 從指定學校抓取教授的研究領域與近兩年論文
  2. 格式化成與 /data/*.json 完全相容的格式：{ "url": "純文字" }
  3. 可選擇：
     a) 輸出為 JSON 檔案存入 /data/
     b) 直接跑 pipeline 寫入資料庫（chunk + embed + store）

使用方式：
  # 方式一：直接指定教授姓名與學校（互動）
  python -m scripts.professor_fetcher.run_fetch --name "Andrew Ng" --school "Stanford"

  # 方式二：批次模式（從 JSON 設定檔讀入）
  python -m scripts.professor_fetcher.run_fetch --config professors.json

  # 方式三：抓完後直接入庫（不存 JSON）
  python -m scripts.professor_fetcher.run_fetch --name "Fei-Fei Li" --school "Stanford" --embed

  # 方式四：指定已知的 author_id（跳過搜尋步驟）
  python -m scripts.professor_fetcher.run_fetch --author-id "47730H0AAAAJ" --school "Stanford"

設定檔格式 (professors.json)：
  [
    {"name": "Andrew Ng",    "school": "Stanford University",       "school_id": "stanford"},
    {"name": "Yann LeCun",   "school": "New York University",       "school_id": "nyu"}
  ]

環境變數（需在 .env 中設定）：
  SERPAPI_KEY   — SerpAPI 的 API Key
  DATABASE_URL  — PostgreSQL 連線字串（僅在 --embed 模式需要）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
ROOT_DIR = SCRIPTS_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from professor_fetcher.fetcher import (
    search_professor_id,
    fetch_author_profile,
    fetch_recent_papers,
    RECENT_YEARS_CUTOFF,
)
from professor_fetcher.formatter import format_professor_to_json

DATA_DIR = ROOT_DIR / "data"


# ── 學校 school_id 對照表（與 pipeline.py 一致）─────────────────────────────
SCHOOL_ID_MAP: dict[str, str] = {
    "stanford":      "stanford",
    "cmu":           "cmu",
    "carnegie":      "cmu",
    "mit":           "mit",
    "berkeley":      "berkeley",
    "caltech":       "caltech",
    "georgia":       "gatech",
    "gatech":        "gatech",
    "illinois":      "uiuc",
    "uiuc":          "uiuc",
    "cornell":       "cornell",
    "ucla":          "ucla",
    "ucsd":          "ucsd",
    "washington":    "uw",
    "uw":            "uw",
    "nccu":          "nccu",
    "chengchi":      "nccu",
}


def _infer_school_id(school: str) -> str:
    """從學校名稱推斷 school_id。"""
    school_lower = school.lower()
    for key, sid in SCHOOL_ID_MAP.items():
        if key in school_lower:
            return sid
    # 無法識別，用學校名稱第一個單字
    return school_lower.split()[0].replace(".", "")


def fetch_one_professor(
    name: str,
    school: str,
    school_id: str = "",
    author_id: str = "",
    cutoff_year: int | None = None,
    max_papers: int = 20,
    delay: float = 1.0,
) -> dict[str, str] | None:
    """
    抓取單一教授的 Google Scholar 資料，回傳 {url: text} dict。

    Args:
        name:        教授全名
        school:      學校名稱（用於搜尋與文字 context）
        school_id:   學校 ID（用於 pipeline）；若空則自動推斷
        author_id:   若已知直接傳入，跳過搜尋
        cutoff_year: 最早年份（含）；預設為近兩年
        max_papers:  最多抓幾篇近年論文
        delay:       每次 API 呼叫後的延遲秒數（避免 rate limit）

    Returns:
        dict[str, str] 或 None（若失敗）
    """
    print(f"\n{'='*60}")
    print(f"處理教授：{name} @ {school}")

    # Step 1: 取得 author_id
    if not author_id:
        print(f"  搜尋 Google Scholar Profile...")
        author_id = search_professor_id(name, affiliation=school)
        time.sleep(delay)

    if not author_id:
        print(f"找不到 {name} 的 Google Scholar 頁面，跳過。")
        return None

    print(f"  author_id = {author_id}")

    # Step 2: 取得完整 profile
    # (目前免費版 SerpAPI 封鎖完整 profile，為節省配額改直接構造本地 metadata)
    profile_data = fetch_author_profile(author_id)
    # 此步驟無須網路請求，故移除 sleep

    # Step 3: 搜尋近兩年論文
    print(f"  搜尋並過濾近 {RECENT_YEARS_CUTOFF} 年後的論文...")
    recent_papers = fetch_recent_papers(
        author_id=author_id,
        professor_name=name,
        cutoff_year=cutoff_year,
        max_papers=max_papers,
    )
    print(f"  近年論文數：{len(recent_papers)}")

    if recent_papers:
        for p in recent_papers[:3]:  # 預覽前 3 篇
            print(f"    [{p['year']}] {p['title'][:60]}...")

    # Step 4: 格式化
    formatted = format_professor_to_json(
        profile_data=profile_data,
        recent_papers=recent_papers,
        school_name=school,
        professor_name=name,    # ← 新增：當 profile_data 為空時用來組合 profile URL
        author_id=author_id,
    )
    print(f"產生 {len(formatted)} 個 URL entries")

    return formatted


def save_to_json(data: dict[str, str], school_id: str, output_dir: Path) -> Path:
    """
    將資料合併寫入 /data/{school_id}_professors.json。
    若檔案已存在則合併（不覆蓋現有資料，只新增/更新 key）。
    """
    output_path = output_dir / f"{school_id}_professors.json"

    existing: dict[str, str] = {}
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            print(f"已讀取現有檔案 {output_path.name}，含 {len(existing)} 個 entries")
        except json.JSONDecodeError:
            print(f"現有檔案格式錯誤，將重新建立。")

    merged = {**existing, **data}
    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已儲存至 {output_path}（共 {len(merged)} 個 entries）")
    return output_path


def run_pipeline_on_file(json_path: Path) -> None:
    """對指定的 JSON 檔案執行 embedder pipeline（chunk + embed + store）。"""
    from embedder.pipeline import run_pipeline

    # 建立指向該檔案所在目錄的臨時 data dir
    data_dir = json_path.parent
    print(f"\n執行 embedding pipeline，資料目錄：{data_dir}")
    run_pipeline(data_dirname=str(data_dir.relative_to(ROOT_DIR)))


# ── 批次設定檔模式 ────────────────────────────────────────────────────────────

def run_from_config(config_path: Path, embed: bool = False, **kwargs) -> None:
    """從 JSON 設定檔批次抓取多位教授。"""
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config_data, list):
        print("錯誤：設定檔格式應為 list of {name, school, school_id?}。")
        return

    # 按學校分組，最後各自合併成一個 JSON
    school_results: dict[str, dict[str, str]] = {}

    for entry in config_data:
        name = entry.get("name", "")
        school = entry.get("school", "")
        school_id = entry.get("school_id", "") or _infer_school_id(school)
        author_id = entry.get("author_id", "")

        if not name or not school:
            print(f"跳過無效 entry：{entry}")
            continue

        result = fetch_one_professor(
            name=name,
            school=school,
            school_id=school_id,
            author_id=author_id,
            **kwargs,
        )
        if result:
            if school_id not in school_results:
                school_results[school_id] = {}
            school_results[school_id].update(result)

    # 儲存結果
    for sid, data in school_results.items():
        json_path = save_to_json(data, sid, DATA_DIR)
        if embed:
            run_pipeline_on_file(json_path)


# ── 單一教授模式 ─────────────────────────────────────────────────────────────

def run_single(
    name: str,
    school: str,
    school_id: str = "",
    author_id: str = "",
    embed: bool = False,
    **kwargs,
) -> None:
    """抓取單一教授並儲存/入庫。"""
    sid = school_id or _infer_school_id(school)

    result = fetch_one_professor(
        name=name,
        school=school,
        school_id=sid,
        author_id=author_id,
        **kwargs,
    )
    if not result:
        print("未取得任何資料，結束。")
        return

    json_path = save_to_json(result, sid, DATA_DIR)
    if embed:
        run_pipeline_on_file(json_path)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="透過 SerpAPI 抓取 Google Scholar 教授資料，格式化後存入 /data/ 或直接入庫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  # 抓取單一教授（輸出 JSON）
  python -m scripts.professor_fetcher.run_fetch --name "Andrew Ng" --school "Stanford University"

  # 指定已知的 author_id（跳過搜尋）
  python -m scripts.professor_fetcher.run_fetch --author-id "47730H0AAAAJ" --school "Stanford University"

  # 抓完後直接 chunk + embed + 入庫
  python -m scripts.professor_fetcher.run_fetch --name "Fei-Fei Li" --school "Stanford" --embed

  # 批次模式（從設定檔）
  python -m scripts.professor_fetcher.run_fetch --config professors_list.json

  # 批次 + 入庫
  python -m scripts.professor_fetcher.run_fetch --config professors_list.json --embed
        """,
    )

    # 互斥群組：單一教授模式 / 批次設定檔
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--name", type=str, help="教授全名（單一模式）")
    mode_group.add_argument("--config", type=str, help="JSON 設定檔路徑（批次模式）")

    parser.add_argument("--author-id", type=str, default="", help="Google Scholar author_id（單一模式可選，傳入此值可跳過搜尋）")
    parser.add_argument("--school", type=str, default="", help="學校名稱（單一模式必填）")
    parser.add_argument("--school-id", type=str, default="", help="學校 ID（可選，例如 stanford、cmu）")
    parser.add_argument(
        "--cutoff-year",
        type=int,
        default=None,
        help=f"論文最早年份（預設：{RECENT_YEARS_CUTOFF}，即近兩年）",
    )
    parser.add_argument("--max-papers", type=int, default=20, help="每位教授最多抓幾篇近年論文（預設 20）")
    parser.add_argument("--delay", type=float, default=1.0, help="每次 API 呼叫後的延遲秒數（預設 1.0）")
    parser.add_argument(
        "--embed",
        action="store_true",
        help="抓完後自動執行 chunk + embed + 寫入資料庫",
    )

    args = parser.parse_args()

    kwargs = {
        "cutoff_year": args.cutoff_year,
        "max_papers":  args.max_papers,
        "delay":       args.delay,
    }

    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"找不到設定檔：{config_path}")
            sys.exit(1)
        run_from_config(config_path, embed=args.embed, **kwargs)
    else:
        # 單一教授模式（--name）
        if not args.school:
            print("錯誤：必須同時指定 --school（學校名稱）")
            sys.exit(1)
        run_single(
            name=args.name,
            school=args.school,
            school_id=args.school_id,
            author_id=args.author_id,
            embed=args.embed,
            **kwargs,
        )


if __name__ == "__main__":
    main()


