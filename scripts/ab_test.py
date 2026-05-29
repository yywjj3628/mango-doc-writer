#!/usr/bin/env python3
"""
ab_test.py — RAG 路由 A/B 测试运行器

用法：
    python scripts/ab_test.py [article_ids...]

A 组：强制 jiuyou_docs 单库
B 组：使用阶段 19.3 路由

输出：outputs/ab-test/<article_id>/{A,B}/
"""

import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

CASES_DIR = PROJECT_ROOT / "tests" / "cases"
OUTPUT_BASE = PROJECT_ROOT / "outputs" / "ab-test"


def parse_case_file(filepath: str) -> dict:
    """从测试 case 的 Markdown 文件中提取用户需求和用户初稿。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 ## 用户需求 到 ## 用户初稿 之间的内容
    m = re.search(r"## 用户需求\n\n(.*?)(?=\n## )", content, re.DOTALL)
    requirement = m.group(1).strip() if m else ""

    # 提取 ## 用户初稿 到下一个 ## 或文件结尾
    m = re.search(r"## 用户初稿\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    draft = m.group(1).strip() if m else ""

    return {"requirement": requirement, "draft": draft}


def run_test(article_id: str, rag_mode: str) -> dict:
    """
    运行单个 A/B 测试。

    Args:
        article_id: case 文件名（如 001-news）
        rag_mode: "jiuyou_only" | "routed"
    """
    case_file = CASES_DIR / f"{article_id}.md"
    if not case_file.exists():
        print(f"❌ Case not found: {case_file}")
        return {"error": f"Case not found: {case_file}"}

    case_data = parse_case_file(str(case_file))
    if not case_data["requirement"]:
        print(f"❌ No requirement in: {case_file}")
        return {"error": "No requirement"}

    # 设置 RAG 模式环境变量
    if rag_mode == "jiuyou_only":
        os.environ["RAG_FORCE_COLLECTION"] = "jiuyou_docs"
        os.environ["RAG_ENABLE_MULTI_COLLECTION"] = "false"
    else:
        os.environ.pop("RAG_FORCE_COLLECTION", None)
        os.environ["RAG_ENABLE_MULTI_COLLECTION"] = "true"

    from run_pipeline import run_pipeline, save_results
    from pipeline_types import PipelineInput

    input_data = PipelineInput(
        requirement=case_data["requirement"],
        draft=case_data["draft"],
    )

    print(f"  Running {article_id} [{rag_mode}]...")
    start = time.time()
    result = run_pipeline(input_data)
    elapsed = time.time() - start
    print(f"  Done in {elapsed:.1f}s — status: {result.status}")

    # 保存结果
    output_dir = str(OUTPUT_BASE / article_id / rag_mode)
    saved = save_results(output_dir, result)

    # 收集关键信息
    info = {
        "article_id": article_id,
        "rag_mode": rag_mode,
        "status": result.status,
        "elapsed": elapsed,
        "output_dir": output_dir,
        "rag_status": result.pipeline_report.rag_status if result.pipeline_report else None,
        "rag_collections_used": result.pipeline_report.rag_collections_used if result.pipeline_report else None,
        "rag_primary_collection": result.pipeline_report.rag_primary_collection if result.pipeline_report else None,
        "style_references_count": result.pipeline_report.style_references_count if result.pipeline_report else 0,
        "final_markdown": result.final_markdown or "",
        "saved_files": saved,
        "error": result.error,
    }

    # 保存 summary
    summary_path = os.path.join(output_dir, "ab_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    return info


def main():
    # 默认测试 3 篇
    default_articles = ["001-news", "006-leader-speech", "002-fake-report-real-request"]
    articles = sys.argv[1:] if len(sys.argv) > 1 else default_articles

    print(f"=== RAG A/B Test ===")
    print(f"Articles: {articles}")
    print(f"Output: {OUTPUT_BASE}")
    print()

    all_results = []

    for article_id in articles:
        print(f"\n{'='*60}")
        print(f"Article: {article_id}")
        print(f"{'='*60}")

        # A 组
        print(f"\n--- A 组: jiuyou_only ---")
        a_result = run_test(article_id, "jiuyou_only")

        # B 组
        print(f"\n--- B 组: routed ---")
        b_result = run_test(article_id, "routed")

        all_results.append({
            "article_id": article_id,
            "A": a_result,
            "B": b_result,
        })

    # 保存总结果
    master_path = OUTPUT_BASE / "ab_master.json"
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ All done. Master: {master_path}")
    return all_results


if __name__ == "__main__":
    main()
