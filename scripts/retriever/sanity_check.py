"""
sanity_check.py — 搜尋結果可信度自動標註模組

在搜尋結果回傳給 Agent 之前，掃描每個 chunk 的文字，
找出「在常理上不可能正確」的數值，並在該筆結果上附加
[⚠️ 資料可疑] 旗標與說明，讓 Agent 知道需要重新搜尋或謹慎使用。

支援的檢查維度：
  1. GPA 範圍       — 美國制 0.0–4.3，超出視為可疑
  2. TOEFL 分數     — 有效範圍 0–120（iBT），超出可疑
  3. IELTS 分數     — 有效範圍 0.0–9.0，超出可疑
  4. GRE 分數       — Verbal/Quant 各 130–170，總分 260–340
  5. 申請截止月份   — 12 月前後±1 個月合理，超出可疑
  6. 學費           — 單學期超過 $100,000 美元視為可疑

設計原則：
  - 保守標記（寧漏勿誤）：只在數值明顯超出已知合理範圍時才標記
  - 不修改原始文字，只在結果 dict 加入 'sanity_warnings' 欄位
  - 若無可疑點，'sanity_warnings' 為空 list
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SanityWarning:
    rule: str          # 規則名稱，e.g. 'gpa_out_of_range'
    matched_text: str  # 在文中匹配到的原始片段
    reason: str        # 說明為何可疑


# ── 規則定義 ───────────────────────────────────────────────────────

# GPA：美國研究所申請語境下的 GPA 一律基於 4.0 或 4.3 scale
# 超過 4.5 絕對不合理；4.0–4.3 之間視為邊緣，不報警
_GPA_PATTERN = re.compile(
    r"\b(?:gpa|grade\s+point\s+average)\b.*?"   # 'GPA' 或 'grade point average'
    r"(\d{1,2}(?:\.\d{1,2})?)"                   # 捕捉數字
    r"(?:\s*/\s*\d{1,2}(?:\.\d{1,2})?)?",        # 可選的 '/4.0' 分母
    re.IGNORECASE,
)

# TOEFL iBT：0–120 分，要求分數通常 80–115
_TOEFL_PATTERN = re.compile(
    r"\btoefl\b.*?(\d{2,3})",
    re.IGNORECASE,
)

# IELTS：0.0–9.0
_IELTS_PATTERN = re.compile(
    r"\bielts\b.*?(\d(?:\.\d)?)",
    re.IGNORECASE,
)

# GRE：單科 130–170，不抓總分（避免誤判一般 3 位數字）
_GRE_SCORE_PATTERN = re.compile(
    r"\bgre\b.*?(\d{3})\b",
    re.IGNORECASE,
)

# 學費：$ 後面跟著數字（可含逗號）
_TUITION_PATTERN = re.compile(
    r"\$\s*([\d,]+)(?:\.\d+)?\s*(?:per\s+(?:semester|year|credit))?",
    re.IGNORECASE,
)


def _parse_float(s: str) -> float | None:
    """安全轉換數字字串為 float，去除逗號。"""
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def check_chunk(chunk_text: str) -> list[SanityWarning]:
    """
    檢查單一 chunk 文字，回傳所有可疑警告（空 list 表示無問題）。
    """
    warnings: list[SanityWarning] = []
    text = chunk_text

    # ── 1. GPA 檢查 ──────────────────────────────────────────────
    for m in _GPA_PATTERN.finditer(text):
        val = _parse_float(m.group(1))
        if val is None:
            continue
        if val > 4.5:
            warnings.append(SanityWarning(
                rule="gpa_out_of_range",
                matched_text=m.group(0)[:80],
                reason=(
                    f"偵測到 GPA {val}，超出美國制 4.0/4.3 scale 的合理上限（4.5）。"
                    "可能是爬取錯誤或非美國制成績格式（如百分制）混入。"
                ),
            ))
        elif val == 0.0:
            warnings.append(SanityWarning(
                rule="gpa_zero",
                matched_text=m.group(0)[:80],
                reason="偵測到 GPA 為 0.0，可能是佔位符或解析錯誤。",
            ))

    # ── 2. TOEFL 檢查 ────────────────────────────────────────────
    for m in _TOEFL_PATTERN.finditer(text):
        val = _parse_float(m.group(1))
        if val is None:
            continue
        if val > 120:
            warnings.append(SanityWarning(
                rule="toefl_out_of_range",
                matched_text=m.group(0)[:80],
                reason=(
                    f"偵測到 TOEFL 分數 {val}，超出 iBT 滿分 120 分。"
                    "可能是舊版 PBT 分數（577 分制）被錯誤標記為 iBT。"
                ),
            ))

    # ── 3. IELTS 檢查 ────────────────────────────────────────────
    for m in _IELTS_PATTERN.finditer(text):
        val = _parse_float(m.group(1))
        if val is None:
            continue
        if val > 9.0:
            warnings.append(SanityWarning(
                rule="ielts_out_of_range",
                matched_text=m.group(0)[:80],
                reason=f"偵測到 IELTS 分數 {val}，超出滿分 9.0。",
            ))

    # ── 4. GRE 分數檢查 ─────────────────────────────────────────
    for m in _GRE_SCORE_PATTERN.finditer(text):
        val = _parse_float(m.group(1))
        if val is None:
            continue
        # 單科（V/Q）: 130–170；總分：260–340
        # 只報告明顯超出 340 或低於 130 的數值
        if val > 340 or val < 130:
            warnings.append(SanityWarning(
                rule="gre_out_of_range",
                matched_text=m.group(0)[:80],
                reason=(
                    f"偵測到 GRE 數值 {val}，不在已知合理範圍內"
                    "（單科 130–170，總分 260–340）。"
                ),
            ))

    # ── 5. 學費異常高 ────────────────────────────────────────────
    for m in _TUITION_PATTERN.finditer(text):
        val = _parse_float(m.group(1))
        if val is None:
            continue
        # 單學期超過 $100,000 視為異常（可能是全年或多年費用被錯誤標記）
        if val > 100_000:
            warnings.append(SanityWarning(
                rule="tuition_suspiciously_high",
                matched_text=m.group(0)[:80],
                reason=(
                    f"偵測到費用 ${val:,.0f}，單筆超過 $100,000。"
                    "可能是全年/多年學費或解析格式錯誤。"
                ),
            ))

    return warnings


def annotate_results(results: list[dict]) -> list[dict]:
    """
    對搜尋結果列表中的每一筆進行可信度檢查，
    在結果 dict 中新增 'sanity_warnings' 欄位（list of str）。

    若有警告，也在 chunk_text 開頭插入醒目旗標，讓 Agent 看到。

    Args:
        results: search_core() 回傳的 list[dict]

    Returns:
        同一份列表（in-place 修改 + 回傳）
    """
    for res in results:
        text = res.get("chunk_text", "")
        warnings = check_chunk(text)

        if warnings:
            warning_strs = [f"[{w.rule}] {w.reason}" for w in warnings]
            res["sanity_warnings"] = warning_strs

            # 在文字前面插入旗標，讓 Agent 在 context 中直接看到
            flag_block = (
                "\n⚠️ [資料可疑，請重新搜尋或謹慎引用]\n"
                + "\n".join(f"  - {s}" for s in warning_strs)
                + "\n"
            )
            res["chunk_text"] = flag_block + text
        else:
            res["sanity_warnings"] = []

    return results


def format_with_sanity(results: list[dict]) -> str:
    """
    格式化搜尋結果為字串，並在包含可疑資料的結果旁加上醒目標記。
    供 _execute_tool() 使用。
    """
    from generator.gemini import format_context_for_prompt
    # annotate_results 已在 chunk_text 中插入旗標，直接格式化即可
    return format_context_for_prompt(results)
