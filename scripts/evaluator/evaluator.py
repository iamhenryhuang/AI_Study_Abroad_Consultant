"""
RAG 評估指標模組
================
提供四種標準 RAG 評估指標：
  - Recall@k            : 前 k 篇中能覆蓋多少 Ground Truth 文件
  - Context Precision   : 依 RAGAS 定義，檢索結果中相關文件的排名加權精確率
  - Context Recall      : 所有 GT 文件被完整檢索到的比例 (不考慮排序)
  - F1 Score            : Token-level F1，評估生成回答與 GT 回答的字詞重合度 (支援中英文混合)

公式參考:
  - RAGAS Context Precision: https://docs.ragas.io/en/stable/concepts/metrics/context_precision.html
  - SQuAD F1: https://rajpurkar.github.io/SQuAD-explorer/
"""
import collections
import string
from typing import List, Any


# CJK Unicode 區段（涵蓋常用中日韓字元）
_CJK_RANGES = [
    ('\u4e00', '\u9fff'),   # CJK Unified Ideographs (基本)
    ('\u3400', '\u4dbf'),   # CJK Extension A
    ('\u20000', '\u2a6df'), # CJK Extension B (Supplementary, str comparison ok)
    ('\uf900', '\ufaff'),   # CJK Compatibility Ideographs
    ('\u3040', '\u30ff'),   # Hiragana + Katakana (日文假名也逐字 tokenize)
]


def _is_cjk(char: str) -> bool:
    """判斷單一字元是否為 CJK（中日韓）字元。"""
    return any(lo <= char <= hi for lo, hi in _CJK_RANGES)


class RAGEvaluator:
    """
    RAG 系統的評估工具。

    檢索評估 (Retrieval Metrics):
        - recall_at_k()       — 前 K 個結果的召回率
        - context_precision() — 依 RAGAS 定義的排名加權精確率
        - context_recall()    — 與排名無關的整體召回率

    生成評估 (Generation Metrics):
        - f1_score()          — Token-level F1（SQuAD 版本）

    使用範例:
        evaluator = RAGEvaluator()
        r = evaluator.recall_at_k(retrieved, relevant, k=5)
        cp = evaluator.context_precision(retrieved, relevant)
        cr = evaluator.context_recall(retrieved, relevant)
        f1 = evaluator.f1_score(prediction, ground_truth)
    """

    # ------------------------------------------------------------------
    # Retrieval Metrics
    # ------------------------------------------------------------------

    @staticmethod
    def recall_at_k(
        retrieved_docs: List[Any],
        relevant_docs: List[Any],
        k: int,
    ) -> float:
        """
        計算 Recall@k：前 k 個檢索結果能覆蓋的 GT 文件比例。

        公式: |Relevant ∩ Retrieved[:k]| / |Relevant|

        Args:
            retrieved_docs: 依相關度排序的檢索結果 (doc ID / doc 物件)。
            relevant_docs:  真實相關文件集合 (Ground Truth)。
            k:              考量前 k 篇，必須 >= 1。

        Returns:
            float in [0.0, 1.0]。若 relevant_docs 為空，回傳 0.0。

        Raises:
            ValueError: 若 k < 1。
        """
        if k < 1:
            raise ValueError(f"k 必須 >= 1，收到 k={k}")
        if not relevant_docs:
            return 0.0
        if not retrieved_docs:
            return 0.0

        relevant_set = set(relevant_docs)
        retrieved_k = retrieved_docs[:k]
        hits = sum(1 for doc in retrieved_k if doc in relevant_set)
        return hits / len(relevant_set)

    @staticmethod
    def context_precision(
        retrieved_docs: List[Any],
        relevant_docs: List[Any],
    ) -> float:
        """
        計算 Context Precision（依照 RAGAS 定義）。

        對每個排名位置 k，若第 k 篇是相關的，則計算 P@k（前 k 篇中相關比例），
        再對所有相關文件的位置取平均。分母是「實際被找到的相關文件數」而非全部 GT 文件數。

        公式（RAGAS 版）:
            ContextPrecision = (Σ_{k:doc_k∈R} P@k) / |{k : doc_k ∈ R}|
            其中 P@k = (前 k 篇中的相關篇數) / k

        這與傳統 MAP（Mean Average Precision）的差異在於分母：
          - MAP 分母 = |所有 GT 文件數|（即使未被找到也計入）
          - RAGAS 分母 = |被找到的相關文件數|（只對找到的部分平均）
        RAGAS 版分母更符合「前 k 個結果的精確率」語意。

        Args:
            retrieved_docs: 依相關度排序的檢索結果。
            relevant_docs:  Ground Truth 相關文件。

        Returns:
            float in [0.0, 1.0]。
            若 relevant_docs 為空或 retrieved_docs 為空，回傳 0.0。
            若找不到任何相關文件（0 hits），回傳 0.0。
        """
        if not relevant_docs or not retrieved_docs:
            return 0.0

        relevant_set = set(relevant_docs)
        hits = 0
        sum_precision_at_k = 0.0

        for i, doc in enumerate(retrieved_docs):
            if doc in relevant_set:
                hits += 1
                precision_at_k = hits / (i + 1)  # P@(i+1)
                sum_precision_at_k += precision_at_k

        if hits == 0:
            return 0.0

        # 分母 = 找到的相關文件數（RAGAS 標準）
        return sum_precision_at_k / hits

    @staticmethod
    def context_recall(
        retrieved_docs: List[Any],
        relevant_docs: List[Any],
    ) -> float:
        """
        計算 Context Recall：不考慮排序，所有 GT 文件被檢索到的比例。

        公式: |Relevant ∩ Retrieved| / |Relevant|

        Args:
            retrieved_docs: 所有被檢索到的文件（不限數量，不考慮排序）。
            relevant_docs:  Ground Truth 相關文件。

        Returns:
            float in [0.0, 1.0]。若 relevant_docs 為空，回傳 0.0。
        """
        if not relevant_docs:
            return 0.0
        if not retrieved_docs:
            return 0.0

        relevant_set = set(relevant_docs)
        retrieved_set = set(retrieved_docs)
        hits = len(relevant_set & retrieved_set)
        return hits / len(relevant_set)

    # ------------------------------------------------------------------
    # Generation Metrics
    # ------------------------------------------------------------------

    @staticmethod
    def _get_tokens(text: str) -> List[str]:
        """
        對文字做 Token 化，支援中英文混合。

        規則:
          - 英文: 轉小寫，以空白或 CJK 邊界切詞，去除標點。
          - CJK 字元 (中文/日文假名等): 每個字元視為獨立 token。
          - 標點符號（英文 + 中文常見標點）全部過濾。

        Args:
            text: 輸入文字字串。

        Returns:
            Token 列表。
        """
        if not text:
            return []

        # 中文標點集合
        chinese_punc = set('，。！？；：「」『』、【】（）《》…—～·')
        en_punc = set(string.punctuation)
        all_punc = chinese_punc | en_punc

        text = str(text).lower()

        tokens: List[str] = []
        current_en: List[str] = []

        def flush_en():
            if current_en:
                word = ''.join(current_en)
                if word:  # 確保非空
                    tokens.append(word)
                current_en.clear()

        for char in text:
            if _is_cjk(char):
                flush_en()
                tokens.append(char)
            elif char in all_punc:
                # 標點符號視為分隔符，丟棄但觸發英文斷詞
                flush_en()
            elif char.isspace():
                flush_en()
            else:
                current_en.append(char)

        flush_en()
        return tokens

    @staticmethod
    def f1_score(prediction: str, ground_truth: str) -> float:
        """
        計算 Token-level F1 分數（SQuAD 版本，支援中英文混合）。

        評估生成回答與 Ground Truth 在字詞重合上的 F1，
        計算方式與 SQuAD 評估腳本一致。

        公式:
            precision = |common_tokens| / |prediction_tokens|
            recall    = |common_tokens| / |ground_truth_tokens|
            F1        = 2 * precision * recall / (precision + recall)

        其中 common_tokens 是兩者 token bag（Counter）的交集。

        Args:
            prediction:   模型生成的回答字串。
            ground_truth: Ground Truth 回答字串。

        Returns:
            float in [0.0, 1.0]。
            特殊情況：
              - 兩者都為空字串 → 1.0（完美匹配）
              - 其中一方為空 → 0.0
              - 無任何共同 token → 0.0
        """
        pred_tokens = RAGEvaluator._get_tokens(prediction)
        gt_tokens = RAGEvaluator._get_tokens(ground_truth)

        # 邊界處理：兩者皆空 → 完美匹配；一方為空 → 0
        if len(pred_tokens) == 0 and len(gt_tokens) == 0:
            return 1.0
        if len(pred_tokens) == 0 or len(gt_tokens) == 0:
            return 0.0

        common = collections.Counter(pred_tokens) & collections.Counter(gt_tokens)
        num_same = sum(common.values())

        if num_same == 0:
            return 0.0

        precision = num_same / len(pred_tokens)
        recall    = num_same / len(gt_tokens)
        f1        = (2 * precision * recall) / (precision + recall)
        return f1


# ------------------------------------------------------------------
# 批次評估輔助函數
# ------------------------------------------------------------------

def evaluate_batch(
    queries: List[dict],
    k: int = 5,
) -> dict:
    """
    對多組 query 批次計算所有評估指標，並回傳各指標的平均值。

    每個 query dict 格式:
    {
        "retrieved_docs":  list,  # 依相關度排序的檢索結果 ID
        "relevant_docs":   list,  # Ground Truth 文件 ID
        "prediction":      str,   # 模型生成的文字回答
        "ground_truth":    str,   # Ground Truth 文字回答
    }

    Args:
        queries: query 資料列表。
        k:       Recall@k 中的 k 值，預設 5。

    Returns:
        {
            "recall_at_k":        float,
            "context_precision":  float,
            "context_recall":     float,
            "f1_score":           float,
            "num_queries":        int,
        }
    """
    if not queries:
        return {
            "recall_at_k": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "f1_score": 0.0,
            "num_queries": 0,
        }

    ev = RAGEvaluator
    scores = {
        "recall_at_k": [],
        "context_precision": [],
        "context_recall": [],
        "f1_score": [],
    }

    for q in queries:
        scores["recall_at_k"].append(
            ev.recall_at_k(q["retrieved_docs"], q["relevant_docs"], k=k)
        )
        scores["context_precision"].append(
            ev.context_precision(q["retrieved_docs"], q["relevant_docs"])
        )
        scores["context_recall"].append(
            ev.context_recall(q["retrieved_docs"], q["relevant_docs"])
        )
        scores["f1_score"].append(
            ev.f1_score(q["prediction"], q["ground_truth"])
        )

    n = len(queries)
    return {
        "recall_at_k":       sum(scores["recall_at_k"])       / n,
        "context_precision": sum(scores["context_precision"]) / n,
        "context_recall":    sum(scores["context_recall"])     / n,
        "f1_score":          sum(scores["f1_score"])           / n,
        "num_queries":       n,
    }


# ------------------------------------------------------------------
# 單元測試（直接執行此腳本時觸發）
# ------------------------------------------------------------------

if __name__ == "__main__":
    ev = RAGEvaluator()
    passed = 0
    failed = 0

    def check(name: str, got: float, expected: float, tol: float = 1e-4):
        global passed, failed
        ok = abs(got - expected) <= tol
        status = "PASS" if ok else "❌ FAIL"
        print(f"  {status} | {name}: got={got:.6f}, expected={expected:.6f}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print("【Recall@k 測試】")
    retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    relevant  = ["doc2", "doc5", "doc9"]

    check("Recall@1 (無命中)",   ev.recall_at_k(retrieved, relevant, 1),  0.0)
    check("Recall@2 (1 hit/3)", ev.recall_at_k(retrieved, relevant, 2),  1/3)
    check("Recall@5 (2 hit/3)", ev.recall_at_k(retrieved, relevant, 5),  2/3)
    check("空 retrieved",        ev.recall_at_k([], relevant, 3),          0.0)
    check("空 relevant",         ev.recall_at_k(retrieved, [], 3),         0.0)

    try:
        ev.recall_at_k(retrieved, relevant, 0)
        print("FAIL | k=0 應丟出 ValueError")
        failed += 1
    except ValueError:
        print("PASS | k=0 正確丟出 ValueError")
        passed += 1

    print()
    print("【Context Precision 測試 (RAGAS 版)】")
    # retrieved: doc1, doc2, doc3, doc4；relevant: doc2, doc3
    # i=1 → hit=1, P@2=1/2; i=2 → hit=2, P@3=2/3; sum=1/2+2/3=7/6; hits=2 → 7/12
    r1 = ["doc1", "doc2", "doc3", "doc4"]
    g1 = ["doc2", "doc3"]
    check("一般情況 (7/12)",     ev.context_precision(r1, g1), 7/12)

    # 相關文件在最前面：doc1 命中，P@1=1，hits=1 → 1.0
    r2 = ["doc1", "doc2", "doc3"]
    g2 = ["doc1"]
    check("最前面命中 → 1.0",   ev.context_precision(r2, g2), 1.0)

    # 無命中
    r3 = ["doc1", "doc2"]
    g3 = ["doc5", "doc6"]
    check("無命中 → 0.0",       ev.context_precision(r3, g3), 0.0)

    print()
    print("【Context Recall 測試】")
    check("2 hit / 3 relevant",  ev.context_recall(["doc1","doc2","doc3"], ["doc2","doc3","doc9"]), 2/3)
    check("全命中",              ev.context_recall(["doc1","doc2"],         ["doc1","doc2"]),        1.0)
    check("零命中",              ev.context_recall(["doc1"],                ["doc2"]),               0.0)
    check("空 retrieved",        ev.context_recall([],                      ["doc1"]),               0.0)

    print()
    print("【F1 Score 測試 (token-level)】")
    # 兩者完全相同
    check("完全相同 → 1.0",             ev.f1_score("hello world", "hello world"), 1.0)
    # 無重疊
    check("無重疊 → 0.0",               ev.f1_score("apple",       "banana"),      0.0)
    # 兩者都空
    check("兩者皆空 → 1.0",             ev.f1_score("",             ""),            1.0)
    # 其中一方為空
    check("一方為空 → 0.0",             ev.f1_score("hello",        ""),            0.0)
    # 部分重疊（中文）
    # pred: 台灣 大學 位於 台北 市, gt: 台灣 大學 在 台北
    # common: 台,灣,大,學,台,北 = {台:2,灣:1,大:1,學:1,北:1}
    # pred_tokens: 台灣大學位於台北市 → 9 tokens
    # gt_tokens: 台灣大學在台北 → 7 tokens
    f1_zh = ev.f1_score("台灣大學位於台北市", "台灣大學在台北")
    print(f"中文部分重疊 F1: {f1_zh:.6f} (manual verify)")

    print()
    print("【批次評估 evaluate_batch 測試】")
    batch = [
        {
            "retrieved_docs": ["doc1", "doc2", "doc3"],
            "relevant_docs":  ["doc2", "doc3"],
            "prediction":     "CMU requires a GPA of 3.5",
            "ground_truth":   "CMU requires GPA 3.5 or above",
        },
        {
            "retrieved_docs": ["doc4", "doc5"],
            "relevant_docs":  ["doc4"],
            "prediction":     "Stanford deadline is December 1st",
            "ground_truth":   "Stanford deadline is December 1st",
        },
    ]

    result = evaluate_batch(batch, k=3)
    print(f"  Recall@3:        {result['recall_at_k']:.4f}")
    print(f"  Context Prec:    {result['context_precision']:.4f}")
    print(f"  Context Recall:  {result['context_recall']:.4f}")
    print(f"  F1 (avg):        {result['f1_score']:.4f}")
    print(f"  Queries:         {result['num_queries']}")

    print()
    print("=" * 60)
    print(f"測試結果: {passed} passed, {failed} failed")
    if failed == 0:
        print("全部通過！")
    else:
        print("有測試未通過，請檢查邏輯。")
