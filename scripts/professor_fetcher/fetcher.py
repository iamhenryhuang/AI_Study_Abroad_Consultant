"""
fetcher.py — SerpAPI Google Scholar 教授資料抓取模組（重設計版）

根據實際測試，SerpAPI 的 engine 可用性如下：
  - google_scholar          正常（搜尋論文）
  - google_scholar_author   回傳空資料（可能被擋）
  - google_scholar_profiles 已停用（400 + "discontinued"）

因此本模組改用以下策略：
  1. search_professor_id()  — 用 google_scholar engine 搜尋 "{name} {school}" ，
                              從論文結果的 publication_info.authors[].link 中取出 author_id
  2. fetch_papers_by_search() — 繼續用 google_scholar 搜尋該教授的論文，
                                 過濾近兩年的結果
  3. fetch_author_profile()   — 嘗試用 google_scholar_author engine；
                                 若失敗則從搜尋結果組合 profile

環境變數：
  SERPAPI_KEY — SerpAPI 的 API Key（必填）
  申請：https://serpapi.com（每月 250 次免費）
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
            resp = requests.get(SERPAPI_BASE, params=all_params, timeout=30)

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
            time.sleep(2 ** attempt)

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
      - 使用 q="{name}" {affiliation} 搜尋
      - 掃描前 10 筆論文的 publication_info.authors
      - 找名字最接近 {name} 的 author，取其 Google Scholar link 中的 user= 參數

    Args:
        name:        教授全名，例如 "Andrew Ng"
        affiliation: 學校關鍵字，例如 "Stanford"

    Returns:
        Google Scholar author_id 或 None
    """
    query = f'"{name}" {affiliation}'.strip()
    print(f'  搜尋：{query!r}')

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
    name_parts = set(name.lower().split())

    best_id = None
    best_score = 0

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

            # 計算名字匹配分數（縮寫也算分）
            author_parts = set(author_name.lower().split("."))
            author_parts.update(author_name.lower().split())
            score = 0
            for np in name_parts:
                for ap in author_parts:
                    if np == ap or (len(np) > 1 and np[0] == ap[0] and len(ap) == 1):
                        score += 1
            if score > best_score:
                best_score = score
                best_id = author_id
                print(
                    f"  候選 author：{author_name!r} "
                    f"(score={score}, id={author_id})"
                )

    if best_id:
        print(f"選定 author_id={best_id}")
    else:
        print(f"無法從搜尋結果中找到 {name!r} 的 author_id")
        print(f"請手動前往 https://scholar.google.com 搜尋，")
        print(f"取得 URL 中的 user=XXXXXX，然後用 --author-id 參數傳入")

    return best_id


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
