"""
fetcher.py — SerpAPI Google Scholar 教授資料抓取模組

搜尋策略（已簡化）：
  1. search_professor_id()       — 用 google_scholar engine 搜尋 "{name}" "{school}"，
                                   從論文結果的 publication_info.authors[].link 中取出 author_id
  2. fetch_recent_papers()       — 搜尋該教授的近兩年論文，過濾年份
  3. fetch_author_profile()      — 返回基本的 author_id metadata（節省 API 配額）
  4. fetch_school_cs_professors() — 搜尋學校全體教授（不限定學科）

環境變數：
  SERPAPI_KEY — SerpAPI 的 API Key（必填）
  申請：https://serpapi.com（每月 100 次免費試用額度）
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY: str = os.environ.get("SERPAPI_KEY", "")
SERPAPI_BASE = "https://serpapi.com/search"

_THIS_YEAR = datetime.now().year
RECENT_YEARS_CUTOFF = _THIS_YEAR - 2   # e.g. 2026 → 取 2024、2025、2026

_PLACEHOLDER_KEYS = {"your_serpapi_key_here", "your_key_here", "", "YOUR_KEY"}


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _validate_key() -> None:
    key = SERPAPI_KEY.strip()
    if not key or key in _PLACEHOLDER_KEYS or len(key) < 20:
        raise RuntimeError(
            "\nSERPAPI_KEY 未設定或仍是預設值！\n\n"
            "請按照以下步驟設定：\n"
            "  1. 前往 https://serpapi.com 取得 API Key\n"
            "  2. 在 .env 中設定：SERPAPI_KEY=你的實際key\n\n"
            "或使用 --author-id 直接跳過搜尋（從 Google Scholar 個人頁 URL 取得）\n"
        )


def _get(params: dict) -> dict:
    """呼叫 SerpAPI，回傳 JSON dict；遇到 400 印出 SerpAPI 的錯誤訊息。"""
    _validate_key()
    all_params = {**params, "api_key": SERPAPI_KEY.strip()}

    for attempt in range(3):
        try:
            # 增加超時時間到 120 秒以應對 SerpAPI 伺服器響應慢的情況
            resp = requests.get(SERPAPI_BASE, params=all_params, timeout=120)

            if resp.status_code == 400:
                try:
                    err = resp.json().get("error", resp.text[:200])
                except Exception:
                    err = resp.text[:200]
                raise requests.HTTPError(
                    f"SerpAPI 400 Bad Request（engine={params.get('engine')}）: {err}",
                    response=resp,
                )

            resp.raise_for_status()
            return resp.json()

        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code in (400, 401, 403):
                    raise
            if attempt == 2:
                raise
            print(f"  [retry {attempt + 1}/3] {type(e).__name__}: {str(e)[:100]}")
            time.sleep(2 ** attempt)

        except requests.RequestException as e:
            if attempt == 2:
                raise
            print(f"  [retry {attempt + 1}/3] 網路錯誤：{e}")
            # 重試時增加更長的等待時間（4秒、8秒）
            time.sleep(min(2 ** (attempt + 1), 10))

    return {}


def _extract_author_id_from_url(url: str) -> str | None:
    """從 Google Scholar URL 提取 user= 參數（author_id）。"""
    m = re.search(r"[?&]user=([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def _extract_year_from_snippet(snippet: str, publication: str) -> int | None:
    """從 snippet 或 publication 字串中找年份（4 位數字）。"""
    for text in (publication, snippet):
        m = re.search(r"\b(20\d{2}|19\d{2})\b", text or "")
        if m:
            return int(m.group(1))
    return None


# ── 主要功能：搜尋 author_id ─────────────────────────────────────────────────

def search_professor_id(name: str, affiliation: str = "") -> str | None:
    """
    透過 google_scholar engine 搜尋教授論文，從論文的 author 連結提取 author_id。

    搜尋策略：
      - 使用 q="{name}" {school_name} 組合搜尋（不限定特定學科）
      - 掃描前 10 筆論文的 publication_info.authors
      - 找名字最接近 {name} 的 author，取其 Google Scholar link 中的 user= 參數
      - 警告：對於常見名字（如"xiao long wang"），建議多出現同名人，建議手動指定 author_id

    Args:
        name:        教授全名，例如 "Andrew Ng"
        affiliation: 學校名稱或關鍵字，例如 "Stanford University"

    Returns:
        Google Scholar author_id 或 None
    """
    # 組合查詢：教授名字 + 學校名稱（不含任何學科限制）
    if affiliation:
        query = f'"{name}" "{affiliation}"'
    else:
        query = f'"{name}"'
    
    print(f'  搜尋：{query!r}（名字+學校）')

    try:
        params = {
            "engine": "google_scholar",
            "q": query,
            "hl": "en",
            "num": 10,
        }
        data = _get(params)
    except Exception as e:
        print(f"搜尋失敗：{e}")
        return None

    organic = data.get("organic_results", [])
    if not organic:
        print("搜尋無結果")
        return None

    # 建立姓名關鍵字集（用於比對）
    name_parts = name.lower().split()

    best_id = None
    best_score = 0
    candidates = []  # 保存所有候選人

    for result in organic:
        pub_info = result.get("publication_info", {})
        authors = pub_info.get("authors", [])
        for author in authors:
            author_name = author.get("name", "")
            link = author.get("link", "") or author.get("serpapi_scholar_link", "")
            author_id = _extract_author_id_from_url(link)
            if not author_id:
                # 嘗試從 serpapi_scholar_link 的 author_id 參數取
                slink = author.get("serpapi_scholar_link", "")
                m = re.search(r"author_id=([A-Za-z0-9_-]+)", slink)
                author_id = m.group(1) if m else None
            if not author_id:
                continue

            # 更嚴格的名字匹配：計算編輯距離並檢查主要部分是否相符
            author_parts = author_name.lower().split()
            
            # 計算匹配分數：完全詞匹配優先，部分匹配次之
            score = 0
            matched_parts = 0
            for np in name_parts:
                for ap in author_parts:
                    if np == ap:
                        score += 2  # 完全匹配
                        matched_parts += 1
                    elif len(np) > 2 and len(ap) > 2 and np[0] == ap[0]:
                        score += 1  # 首字母匹配
            
            # 過濾：必須至少匹配 name_parts 的 2/3 以上
            min_matches = max(2, len(name_parts) // 2)
            if matched_parts < min_matches and score < len(name_parts):
                continue  # 匹配度太低，跳過
            
            candidates.append({
                "name": author_name,
                "id": author_id,
                "score": score,
            })
            
            if score > best_score:
                best_score = score
                best_id = author_id
                print(
                    f"  候選 author：{author_name!r} "
                    f"(score={score}, id={author_id})"
                )

    if best_id:
        # 如果有多個高分候選，提示用戶
        high_score_candidates = [c for c in candidates if c["score"] >= best_score - 1]
        if len(high_score_candidates) > 1:
            print(f"\n⚠️  警告：發現多位同分或接近分數的候選人，可能存在同名人員")
            for c in high_score_candidates:
                print(f"    - {c['name']} (score={c['score']}, id={c['id']})")
            print(f"  若非預期人員，建議使用 --author-id 手動指定")
        
        print(f"選定 author_id={best_id}")
    else:
        print(f"無法從搜尋結果中找到 {name!r} 的 author_id")
        print(f"請手動前往 https://scholar.google.com 搜尋，")
        print(f"取得 URL 中的 user=XXXXXX，然後用 --author-id 參數傳入")

    return best_id


def fetch_school_cs_professors(school: str, limit: int = None) -> list[dict[str, Any]]:
    """
    透過 Google Scholar 網站搜尋尋找指定學校的教授。
    搜尋 query: site:scholar.google.com/citations?user= "{school}"
    
    （改為只按學校搜尋，不限制科系，避免遺漏跨領域教授）

    Args:
        school: 學校名稱，例如 "Stanford University"
        limit: 最多抓取幾位教授，測試時可設較小數值避免超過額度

    Returns:
        list of dict，每個 dict 包含:
          - name: 教授名稱
          - author_id: Google Scholar author_id
          - snippet: 搜尋結果的 snippet（可能包含研究領域等）
    """
    # 改為只用學校名稱搜尋，不限制 "Computer Science"
    query = f'site:scholar.google.com/citations?user= "{school}"'
    print(f"  搜尋 {school} 的教授（按名字+學校）：{query!r}")

    professors = []
    
    # 這裡我們只抓第一頁（或前幾頁）的結果，使用 num=20 來一次取得盡量多
    try:
        params = {
            "engine": "google",
            "q": query,
            "hl": "en",
            "num": limit if limit and limit <= 100 else 100, # 預設一頁最多抓 100 筆
        }
        data = _get(params)
    except Exception as e:
        print(f"學校教授搜尋失敗：{e}")
        return []

    organic = data.get("organic_results", [])
    if not organic:
        print("搜尋無結果")
        return []

    for result in organic:
        title = result.get("title", "")
        # 通常 Google 搜尋結果的 title 會是 "Name - Google Scholar" 或附帶其它資訊
        # 我們假設 title 第一部分就是名字
        name = title.split(" -")[0].strip()
        
        link = result.get("link", "")
        author_id = _extract_author_id_from_url(link)
        
        if not author_id:
            continue
            
        snippet = result.get("snippet", "")
        
        professors.append({
            "name": name,
            "author_id": author_id,
            "snippet": snippet,
        })
        
        if limit and len(professors) >= limit:
            break
            
    print(f"  找到 {len(professors)} 位教授。")
    return professors



# ── 主要功能：取得教授 profile ────────────────────────────────────────────────

def fetch_author_profile(author_id: str) -> dict[str, Any]:
    """
    取得教授 profile。
    由於免費版 SerpAPI 方案中 `google_scholar_author` 幾乎都會被擋（回傳空值），
    為了節省 API 額度並加速執行，此處直接回傳帶有 author_id 的基準 dict。
    其餘資訊將由 formatter 透過傳入的 name 與 school 參數自動補齊。

    Args:
        author_id: Google Scholar author_id

    Returns:
        包含 author_id 的基準 dict
    """
    return {"search_parameters": {"author_id": author_id}}


def fetch_papers_by_search(
    name: str,
    author_id: str,
    cutoff_year: int,
    max_papers: int = 20,
) -> list[dict[str, Any]]:
    """
    用 google_scholar engine 以 author: 搜尋，
    過濾近兩年的論文。這是 google_scholar_author 不可用時的 fallback。

    Args:
        name:        教授全名（用於搜尋 query）
        author_id:   Google Scholar author_id（用於 as_sauthors 參數精確過濾）
        cutoff_year: 最早年份
        max_papers:  最多回傳幾篇

    Returns:
        list of paper dicts
    """
    params = {
        "engine": "google_scholar",
        "q": f'author:"{name}"',
        "hl": "en",
        "num": min(max_papers * 2, 20),
        "as_ylo": cutoff_year,   # 只要 cutoff_year 之後的論文
    }
    # 若有 author_id，用 as_sauthors 精確過濾（減少誤配）
    if author_id:
        params["as_sauthors"] = author_id

    try:
        data = _get(params)
    except Exception as e:
        print(f"論文搜尋失敗：{e}")
        return []

    organic = data.get("organic_results", [])
    papers = []
    for result in organic:
        pub_info = result.get("publication_info", {})
        summary = pub_info.get("summary", "")
        year = _extract_year_from_snippet(result.get("snippet", ""), summary)
        if year and year < cutoff_year:
            continue

        # 取得作者字串
        authors_list = pub_info.get("authors", [])
        authors_str = ", ".join(a.get("name", "") for a in authors_list) if authors_list else ""

        # 取 cited_by 數量
        inline = result.get("inline_links", {})
        cited_by = inline.get("cited_by", {})
        cited_val = cited_by.get("total", 0) if isinstance(cited_by, dict) else 0

        papers.append({
            "title":          result.get("title", ""),
            "link":           result.get("link", result.get("snippet_link", "")),
            "citation_id":    "",   # 搜尋模式沒有 citation_id
            "authors":        authors_str or result.get("publication_info", {}).get("summary", ""),
            "publication":    summary,
            "year":           year or cutoff_year,
            "cited_by_value": cited_val,
            "snippet":        result.get("snippet", ""),
        })
        if len(papers) >= max_papers:
            break

    return papers


# ── 主要功能：近兩年論文 ──────────────────────────────────────────────────────

def fetch_recent_papers(
    author_id: str,
    professor_name: str = "",
    cutoff_year: int | None = None,
    max_papers: int = 20,
) -> list[dict[str, Any]]:
    """
    抓取教授近兩年發表的論文。

    直接使用 `google_scholar` 搜尋 (以 author:"Name" 加上 as_sauthors 精確過濾) 
    來取得論文，因為 `google_scholar_author` 引擎在免費方案不可用。

    Args:
        author_id:       Google Scholar author_id
        professor_name:  教授姓名（搜尋必要參數）
        cutoff_year:     最早年份（含），預設 _THIS_YEAR - 2
        max_papers:      最多回傳幾篇

    Returns:
        list of article dicts
    """
    if cutoff_year is None:
        cutoff_year = RECENT_YEARS_CUTOFF

    if professor_name:
        papers = fetch_papers_by_search(
            name=professor_name,
            author_id=author_id,
            cutoff_year=cutoff_year,
            max_papers=max_papers,
        )
        print(f"  近 {cutoff_year} 年後論文：{len(papers)} 篇")
        return papers

    print(f"無法取得論文資料（未提供教授姓名以進行搜尋）")
    return []
