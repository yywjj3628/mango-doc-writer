#!/usr/bin/env python3
"""
ab_test_rag_only.py — RAG 路由 A/B 测试（仅 RAG 层面对比）

不做完整 pipeline 调用（需要 DeepSeek API），
只对比 A/B 两组 RAG 检索结果，评估路由质量。

用法：
    python scripts/ab_test_rag_only.py
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

CASES_DIR = PROJECT_ROOT / "tests" / "cases"
OUTPUT_BASE = PROJECT_ROOT / "outputs" / "ab-test-rag"


def parse_case_file(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"## 用户需求\n\n(.*?)(?=\n## )", content, re.DOTALL)
    requirement = m.group(1).strip() if m else ""
    m = re.search(r"## 用户初稿\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    draft = m.group(1).strip() if m else ""
    return {"requirement": requirement, "draft": draft}


def run_rag_test(article_id: str, rag_mode: str) -> dict:
    """只调用 RAG 检索，不跑完整 pipeline。"""
    from rag_client import retrieve_style_references

    case_file = CASES_DIR / f"{article_id}.md"
    if not case_file.exists():
        return {"error": f"Not found: {case_file}"}

    case_data = parse_case_file(str(case_file))

    # 设置 RAG 模式
    if rag_mode == "jiuyou_only":
        os.environ["RAG_FORCE_COLLECTION"] = "jiuyou_docs"
        os.environ["RAG_ENABLE_MULTI_COLLECTION"] = "false"
    else:
        os.environ.pop("RAG_FORCE_COLLECTION", None)
        os.environ["RAG_ENABLE_MULTI_COLLECTION"] = "true"

    # 需要推断 doc_type
    if "新闻" in case_data["requirement"]:
        doc_type = "新闻稿"
    elif "讲话" in case_data["requirement"]:
        doc_type = "领导讲话"
    elif "汇报" in case_data["requirement"] or "报告" in case_data["requirement"]:
        doc_type = "汇报材料"
    else:
        doc_type = "其他"

    result = retrieve_style_references(
        doc_type=doc_type,
        requirement=case_data["requirement"],
        draft=case_data["draft"],
        plan_result={},
    )

    return {
        "article_id": article_id,
        "rag_mode": rag_mode,
        "inferred_doc_type": doc_type,
        "rag_status": result["rag_status"],
        "rag_count": result["rag_count"],
        "collections_used": result.get("rag_collections_used", []),
        "primary_collection": result.get("rag_primary_collection"),
        "fallback_collection": result.get("rag_fallback_collection"),
        "style_references": result.get("style_references", []),
        "rag_query": result.get("rag_query", ""),
        "rag_sources": result.get("rag_sources", []),
    }


def analyze_rag_quality(refs: list, mode: str) -> dict:
    """分析 RAG 检索质量。"""
    if not refs:
        return {"total_refs": 0, "error": "No references returned"}

    total_phrases = sum(len(r.get("reference_phrases", [])) for r in refs)
    collections = [r.get("collection", "?") for r in refs]
    doc_types = [r.get("doc_type", "?") for r in refs]
    sources = [r.get("source", "?") for r in refs]
    has_do_not_copy = all(r.get("do_not_copy") for r in refs)
    has_risk_notes = all(r.get("risk_notes") for r in refs)

    return {
        "total_refs": len(refs),
        "total_phrases": total_phrases,
        "collections": collections,
        "doc_types": doc_types,
        "sources": sources,
        "has_do_not_copy": has_do_not_copy,
        "has_risk_notes": has_risk_notes,
        "openclaw_memory_queried": "openclaw_memory" in collections,
    }


def compare_ab(a_result: dict, b_result: dict, article_id: str) -> dict:
    """A/B 对比分析。"""
    a_quality = analyze_rag_quality(a_result.get("style_references", []), "A")
    b_quality = analyze_rag_quality(b_result.get("style_references", []), "B")

    comparison = {
        "article_id": article_id,
        "A": a_result,
        "B": b_result,
        "A_quality": a_quality,
        "B_quality": b_quality,
    }

    # 判断 B 是否优于 A
    b_better = False
    advantages = []
    side_effects = []

    # 1. B 是否查询了 mango_style_docs
    b_has_mango = "mango_style_docs" in (b_result.get("collections_used") or [])
    a_has_mango = "mango_style_docs" in (a_result.get("collections_used") or [])

    if b_has_mango and not a_has_mango:
        b_better = True
        advantages.append("B 组引入了 mango_style_docs 风格参考")

    # 2. B 参考数量是否更多
    if b_quality["total_phrases"] > a_quality["total_phrases"]:
        b_better = True
        advantages.append(f"B 组参考短语更多 ({b_quality['total_phrases']} vs {a_quality['total_phrases']})")

    # 3. B 是否有 openclaw_memory
    if b_quality["openclaw_memory_queried"]:
        side_effects.append("⚠️ B 组查询了 openclaw_memory（违反规则）")

    # 4. B 是否保持安全标记
    if b_quality["has_do_not_copy"] and b_quality["has_risk_notes"]:
        advantages.append("B 组安全标记完整（do_not_copy + risk_notes）")

    comparison["b_better"] = b_better
    comparison["advantages"] = advantages
    comparison["side_effects"] = side_effects

    return comparison


def main():
    articles = {
        "001-news": "新闻稿",
        "006-leader-speech": "领导讲话",
        "002-fake-report-real-request": "汇报材料/请示",
    }

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    print(f"=== RAG A/B Test (RAG Layer Only) ===")
    print(f"Articles: {list(articles.keys())}")
    print()

    all_comparisons = []

    for article_id, doc_type_label in articles.items():
        print(f"\n{'='*60}")
        print(f"  {article_id} ({doc_type_label})")
        print(f"{'='*60}")

        # A 组
        print(f"\n--- A 组: jiuyou_only ---")
        a_result = run_rag_test(article_id, "jiuyou_only")
        a_q = analyze_rag_quality(a_result.get("style_references", []), "A")
        print(f"  collections: {a_result.get('collections_used')}")
        print(f"  count: {a_result.get('rag_count')}")
        print(f"  refs: {a_q['total_refs']}, phrases: {a_q['total_phrases']}")
        print(f"  doc_types: {a_q['doc_types']}")
        print(f"  do_not_copy: {a_q['has_do_not_copy']}, risk_notes: {a_q['has_risk_notes']}")
        if a_result.get("style_references"):
            for i, ref in enumerate(a_result["style_references"]):
                print(f"  ref_{i}: coll={ref.get('collection')}, phrases={len(ref.get('reference_phrases', []))}")
                for p in ref.get("reference_phrases", [])[:2]:
                    print(f"    > {p[:80]}")

        # B 组
        print(f"\n--- B 组: routed ---")
        b_result = run_rag_test(article_id, "routed")
        b_q = analyze_rag_quality(b_result.get("style_references", []), "B")
        print(f"  collections: {b_result.get('collections_used')}")
        print(f"  count: {b_result.get('rag_count')}")
        print(f"  refs: {b_q['total_refs']}, phrases: {b_q['total_phrases']}")
        print(f"  doc_types: {b_q['doc_types']}")
        print(f"  do_not_copy: {b_q['has_do_not_copy']}, risk_notes: {b_q['has_risk_notes']}")
        if b_result.get("style_references"):
            for i, ref in enumerate(b_result["style_references"]):
                print(f"  ref_{i}: coll={ref.get('collection')}, phrases={len(ref.get('reference_phrases', []))}")
                for p in ref.get("reference_phrases", [])[:2]:
                    print(f"    > {p[:80]}")

        # 对比
        comp = compare_ab(a_result, b_result, article_id)
        all_comparisons.append(comp)
        print(f"\n--- 对比 ---")
        print(f"  B 优于 A: {'✅' if comp['b_better'] else '❌'}")
        print(f"  优势: {comp['advantages']}")
        if comp['side_effects']:
            print(f"  副作用: {comp['side_effects']}")

    # 保存结果
    master = OUTPUT_BASE / "ab_rag_master.json"
    with open(master, "w", encoding="utf-8") as f:
        # Convert to JSON-serializable
        for comp in all_comparisons:
            comp["A_quality"].pop("openclaw_memory_queried", None)
            comp["B_quality"].pop("openclaw_memory_queried", None)
        json.dump(all_comparisons, f, ensure_ascii=False, indent=2)

    print(f"\n✅ All done. Master: {master}")
    return all_comparisons


if __name__ == "__main__":
    main()
