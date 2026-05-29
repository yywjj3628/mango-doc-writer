#!/usr/bin/env python3
"""
v0.1.4 阶段 4 三模式对比测试脚本

用法：
    python scripts/run_v014_mode_comparison.py tests/cases/v014-input-A-news-minimal.json
"""

import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SKILL_DIR, "pipeline"))

from pipeline_types import PipelineInput
from run_pipeline import run_pipeline, save_results


def load_json_input(filepath: str) -> dict:
    """加载 JSON 格式测试输入"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def run_mode_comparison(json_path: str, modes: list = None):
    """对同一输入运行三种模式对比"""
    if modes is None:
        modes = ["safe_official", "assisted_expansion", "creative_mimic"]

    data = load_json_input(json_path)
    case_id = data.get("case_id", "unknown")
    case_name = data.get("case_name", "")
    requirement = data.get("requirement", "")
    draft = data.get("draft", "")

    print(f"\n{'='*60}")
    print(f"📋 测试输入 {case_id}: {case_name}")
    print(f"  需求: {requirement[:60]}...")
    print(f"  初稿: {draft[:60]}...")
    print(f"{'='*60}")

    results = {}

    for mode in modes:
        print(f"\n{'─'*40}")
        print(f"🔄 模式: {mode}")
        print(f"{'─'*40}")

        input_data = PipelineInput(
            requirement=requirement,
            draft=draft,
            specified_doc_type=data.get("specified_doc_type"),
            target_unit=data.get("target_unit"),
            scene=data.get("scene"),
            generation_mode=mode,
        )

        start_time = time.time()
        try:
            result = run_pipeline(input_data)
            elapsed = time.time() - start_time
        except Exception as e:
            print(f"  ❌ 运行异常: {e}")
            results[mode] = {"status": "error", "error": str(e)}
            continue

        # 确定输出目录
        case_filename = os.path.splitext(os.path.basename(json_path))[0]
        output_dir = os.path.join(SKILL_DIR, "tests", "reports", f"{case_filename}_{mode}")

        # 保存结果
        saved_files = save_results(output_dir, result)

        # 收集关键信息
        report = result.pipeline_report
        mode_result = {
            "status": result.status,
            "elapsed": f"{elapsed:.1f}s",
            "doc_type": report.doc_type if report else None,
            "risk_level": report.risk_level if report else None,
            "generation_mode": report.generation_mode if report else None,
            "generation_mode_valid": report.generation_mode_valid if report else None,
            "expansion_enabled": report.expansion_enabled if report else None,
            "official_use_allowed": report.official_use_allowed if report else None,
            "quality_gate_pass": report.quality_gate_pass if report else None,
            "quality_gate_threshold": report.quality_gate_threshold if report else None,
            "human_review_required": report.human_review_required if report else None,
            "expansion_report_summary": report.expansion_report_summary if report else None,
            "expansion_review_summary": report.expansion_review_summary if report else None,
            "draft_disclaimer": report.draft_disclaimer if report else None,
            "confirmation_required_count": report.confirmation_required_count if report else None,
            "unsafe_expansion_detected": report.unsafe_expansion_detected if report else None,
            "unsafe_expansion_warnings": report.unsafe_expansion_warnings if report else None,
            "final_markdown_len": len(result.final_markdown or ""),
            "failed_stage": result.failed_stage,
            "error": result.error,
            "output_dir": output_dir,
        }

        # 打印结果
        print(f"  状态: {result.status} ({elapsed:.1f}s)")
        if result.status == "success":
            print(f"  文种: {report.doc_type}")
            print(f"  风险: {report.risk_level}")
            print(f"  质量门禁: {'通过' if report.quality_gate_pass else '未通过'}")
            print(f"  阈值: {report.quality_gate_threshold}")
            print(f"  人工审阅: {report.human_review_required}")
            print(f"  扩写报告: {report.expansion_report_summary}")
            print(f"  official_use_allowed: {report.official_use_allowed}")
            if report.draft_disclaimer:
                print(f"  免责声明: {report.draft_disclaimer[:50]}...")
            if report.unsafe_expansion_detected:
                print(f"  ⚠️ 危险扩写: {report.unsafe_expansion_warnings}")
        else:
            print(f"  失败阶段: {result.failed_stage}")
            print(f"  错误: {result.error}")

        results[mode] = mode_result

    # 对比摘要
    print(f"\n\n{'='*60}")
    print(f"📊 三模式对比摘要 — 输入 {case_id}")
    print(f"{'='*60}")

    for mode, r in results.items():
        print(f"\n  [{mode}]")
        print(f"    状态: {r.get('status')}")
        print(f"    耗时: {r.get('elapsed')}")
        print(f"    expansion_enabled: {r.get('expansion_enabled')}")
        print(f"    official_use_allowed: {r.get('official_use_allowed')}")
        print(f"    质量门禁: {r.get('quality_gate_pass')}")
        print(f"    阈值: {r.get('quality_gate_threshold')}")
        print(f"    人工审阅: {r.get('human_review_required')}")
        print(f"    final_markdown: {r.get('final_markdown_len')} 字符")
        print(f"    unsafe_expansion: {r.get('unsafe_expansion_detected')}")

    return results


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/run_v014_mode_comparison.py <json_case_path>")
        sys.exit(1)

    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"❌ 文件不存在: {json_path}")
        sys.exit(1)

    run_mode_comparison(json_path)


if __name__ == "__main__":
    main()
