"""
formatter.py — 將 SerpAPI Google Scholar 資料格式化為 /data/*.json 相容格式

目標格式（與現有 data/stanford.json 等完全一致）：
    {
        "https://scholar.google.com/citations?user={author_id}":
            "純文字：教授個人資訊 + 研究領域 + 近兩年論文摘要",

        "https://scholar.google.com/citations?view_op=view_citation&...":
            "純文字：單篇論文詳細資訊",
    }

注意：
  - profile_data 可能為空（當 google_scholar_author 不回傳資料時）
  - 此時會改用 professor_name + author_id + school_name 組合基本 profile 文字
"""

from __future__ import annotations

from typing import Any


def _clean(text: str) -> str:
    """移除多餘的空白行與前後空格。"""
    return " ".join(text.split())


def format_professor_to_json(
    profile_data: dict[str, Any],
    recent_papers: list[dict[str, Any]],
    school_name: str = "",
    professor_name: str = "",   # 當 profile_data 為空時的 fallback 姓名
    author_id: str = "",        # 當 profile_data 為空時的 fallback author_id
) -> dict[str, str]:
    """
    將 SerpAPI 回傳的 author profile + 近年論文列表，
    轉換為與 /data/*.json 完全相容的 dict[url, text] 格式。

    若 profile_data 為空（google_scholar_author 不回傳資料時），
    會改用 professor_name / author_id / school_name 組合基本 profile 文字。

    Args:
        profile_data:    fetch_author_profile() 的完整回傳值（可能為空 dict）
        recent_papers:   fetch_recent_papers() 的論文列表
        school_name:     學校名稱，用於補充 context（例如 "Stanford University"）
        professor_name:  教授姓名（profile_data 為空時用）
        author_id:       Google Scholar author_id（profile_data 為空時用）

    Returns:
        dict[str, str]，鍵為 URL，值為純文字，可直接 merge 入現有 JSON 或入庫。
    """
    result: dict[str, str] = {}

    # ── 從 profile_data 提取資訊（若有），否則用 fallback 值 ──────────────
    author_data: dict = (profile_data or {}).get("author", {})
    search_params: dict = (profile_data or {}).get("search_parameters", {})

    # author_id：優先從 search_params 取，fallback 到傳入的 author_id 參數
    resolved_author_id: str = search_params.get("author_id", "") or author_id

    if not resolved_author_id:
        print("formatter: 無法取得 author_id，無法產生 profile URL")
        return result

    # 教授基本資訊（profile 有的話用 profile，沒有的話用傳入的 fallback）
    name = author_data.get("name", "") or professor_name or "Unknown Professor"
    affiliations = author_data.get("affiliations", "") or school_name
    email = author_data.get("email", "")

    # 研究興趣（只有 profile 有資料時才有）
    interests = author_data.get("interests", [])
    interest_titles = [i.get("title", "") for i in interests if isinstance(i, dict)]
    interests_str = ", ".join(filter(None, interest_titles))

    # 引用統計（只有 profile 有資料時才有）
    cited_by_data = (profile_data or {}).get("cited_by", {})
    table = cited_by_data.get("table", [])
    total_citations = 0
    h_index = 0
    for entry in table:
        if isinstance(entry, dict):
            if "citations" in entry:
                total_citations = entry["citations"].get("all", 0)
            for k in ("indice_h", "h_index"):
                if k in entry:
                    h_index = entry[k].get("all", 0)

    # ── 1. 教授 Profile 頁面 URL entry ────────────────────────────────────
    profile_url = f"https://scholar.google.com/citations?user={resolved_author_id}&hl=en"

    profile_lines = [
        f"Professor Profile: {name}",
        f"Affiliation: {affiliations}" if affiliations else "",
        f"School: {school_name}" if school_name and school_name != affiliations else "",
        f"Email: {email}" if email else "",
        f"Research Interests: {interests_str}" if interests_str else "",
        f"Total Citations: {total_citations}" if total_citations else "",
        f"H-Index: {h_index}" if h_index else "",
    ]

    # 近兩年論文摘要
    if recent_papers:
        years = [p["year"] for p in recent_papers if p.get("year")]
        cutoff = min(years) if years else 0
        profile_lines.append("")
        profile_lines.append(
            f"Recent Publications (since {cutoff} — {len(recent_papers)} papers):"
        )
        for paper in recent_papers:
            profile_lines.append(
                f"  [{paper['year']}] {paper['title']} "
                f"(Authors: {paper['authors']}; "
                f"Published in: {paper['publication']}; "
                f"Cited by: {paper['cited_by_value']})"
            )

    # 全部論文列表（只有 profile_data 有時才有）
    all_articles = (profile_data or {}).get("articles", [])
    if all_articles:
        profile_lines.append("")
        profile_lines.append(f"Complete Publication List ({len(all_articles)} total):")
        for article in all_articles[:50]:
            year = article.get("year", "N/A")
            title = article.get("title", "")
            pub = article.get("publication", "")
            cited = article.get("cited_by", {})
            cited_val = cited.get("value", 0) if isinstance(cited, dict) else 0
            profile_lines.append(f"  [{year}] {title} | {pub} | Cited: {cited_val}")

    profile_text = _clean("\n".join(line for line in profile_lines if line is not None))
    if profile_text:
        result[profile_url] = profile_text

    # ── 2. 每篇近年論文各一個 entry ──────────────────────────────────────
    for paper in recent_papers:
        paper_url = paper.get("link", "")
        if not paper_url:
            citation_id = paper.get("citation_id", "")
            if citation_id and resolved_author_id:
                paper_url = (
                    f"https://scholar.google.com/citations"
                    f"?view_op=view_citation&user={resolved_author_id}"
                    f"&citation_for_view={citation_id}&hl=en"
                )
            else:
                continue

        paper_lines = [
            f"Research Paper by Professor {name}",
            f"Title: {paper['title']}",
            f"Authors: {paper['authors']}",
            f"Published in: {paper['publication']}",
            f"Year: {paper['year']}",
            f"Citations: {paper['cited_by_value']}",
        ]
        if paper.get("snippet"):
            paper_lines.append(f"Abstract/Introduction: {paper.get('snippet')}")
        if school_name:
            paper_lines.append(f"Professor Affiliation: {affiliations or school_name}")
        if affiliations and affiliations != school_name:
            paper_lines.append(f"Institution: {affiliations}")
        if interests_str:
            paper_lines.append(f"Professor Research Interests: {interests_str}")

        paper_text = _clean("\n".join(paper_lines))
        if paper_text:
            result[paper_url] = paper_text

    return result
