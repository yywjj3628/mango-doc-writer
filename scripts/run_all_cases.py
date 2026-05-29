"""
运行全部测试 case

用法：
    python scripts/run_all_cases.py
"""

import json
import os
import sys

# 确保 pipeline 目录在 path 中
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SKILL_DIR, "pipeline"))

from run_case import parse_case_file, main as run_single_case


def main():
    cases_dir = os.path.join(SKILL_DIR, "tests", "cases")
    reports_dir = os.path.join(SKILL_DIR, "tests", "reports")

    os.makedirs(reports_dir, exist_ok=True)

    # 收集所有 case 文件
    case_files = sorted([
        f for f in os.listdir(cases_dir)
        if f.endswith(".md")
    ])

    if not case_files:
        print("❌ 未找到测试 case 文件")
        sys.exit(1)

    print(f"📋 找到 {len(case_files)} 个测试 case\n")

    summary = {
        "total_cases": len(case_files),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "cases": [],
    }

    for case_file in case_files:
        case_id = os.path.splitext(case_file)[0]
        case_path = os.path.join(cases_dir, case_file)

        print(f"{'='*60}")
        print(f"🧪 Case: {case_id}")
        print(f"{'='*60}")

        try:
            # 解析 case
            sections = parse_case_file(case_path)
            requirement = sections.get("requirement", "")
            draft = sections.get("draft", "")

            if not requirement or not draft:
                print(f"  ⚠️  case 文件缺少用户需求或初稿，跳过")
                summary["skipped"] += 1
                summary["cases"].append({
                    "case_id": case_id,
                    "status": "skipped",
                    "failed_stage": None,
                    "reason": "case 文件缺少用户需求或初稿",
                })
                print()
                continue

            # 运行 pipeline
            from pipeline_types import PipelineInput
            from run_pipeline import run_pipeline, save_results

            input_data = PipelineInput(
                requirement=requirement,
                draft=draft,
            )
            result = run_pipeline(input_data)

            # 保存结果
            output_dir = os.path.join(reports_dir, case_id)
            save_files = save_results(output_dir, result)

            # 更新汇总
            case_summary = {
                "case_id": case_id,
                "status": result.status,
                "failed_stage": result.failed_stage,
            }

            if result.status == "success" and result.pipeline_report:
                case_summary["review_pass"] = result.pipeline_report.review_pass
                case_summary["rewrite_required"] = result.pipeline_report.rewrite_required
                case_summary["remaining_risk_count"] = result.pipeline_report.remaining_risk_count
                case_summary["manual_confirmation_count"] = result.pipeline_report.manual_confirmation_count

                summary["success"] += 1
            elif result.status == "skipped":
                case_summary["reason"] = result.error or "模型调用器未接入"
                summary["skipped"] += 1
            else:
                case_summary["error"] = result.error
                summary["failed"] += 1

            summary["cases"].append(case_summary)

            print(f"  状态: {result.status}")

        except Exception as e:
            summary["failed"] += 1
            summary["cases"].append({
                "case_id": case_id,
                "status": "failed",
                "failed_stage": None,
                "error": str(e),
            })
            print(f"  ❌ 异常: {e}")

        print()

    # 保存汇总
    summary_path = os.path.join(reports_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 打印汇总
    print(f"{'='*60}")
    print(f"📊 汇总: {summary_path}")
    print(f"  总计: {summary['total_cases']}")
    print(f"  成功: {summary['success']}")
    print(f"  失败: {summary['failed']}")
    print(f"  跳过: {summary['skipped']}")
    print(f"{'='*60}")

    return summary


if __name__ == "__main__":
    main()
