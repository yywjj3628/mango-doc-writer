#!/usr/bin/env python3
"""
run_regression.py — 对指定 case 运行全部回归检查，输出汇总报告。

用法:
  python tests/regression/run_regression.py
  python tests/regression/run_regression.py --cases 002-fake-report-real-request 009-rag-pollution

输出:
  - 控制台汇总
  - tests/reports/regression-summary.json
"""

import argparse
import json
import sys
from pathlib import Path

# 将项目根加入 sys.path，以便 import 同级脚本
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
REPORTS_DIR = PROJECT_DIR / "tests" / "reports"
sys.path.insert(0, str(SCRIPT_DIR))

from check_report import run_check as run_report_check
from check_markdown_claims import run_check as run_md_check, extract_final_markdown, load_watchlist

DEFAULT_CASES = [
    "001-news",
    "002-fake-report-real-request",
    "003-report",
    "004-notice",
    "005-meeting-minutes",
    "006-leader-speech",
    "007-summary",
    "008-letter",
    "009-rag-pollution",
    "010-terminology-risk",
]


def run_single_case(case_id, reports_dir):
    """对单个 case 运行 report 检查 + markdown claims 检查。"""
    report_dir = reports_dir / case_id
    if not report_dir.is_dir():
        return {
            "case_id": case_id,
            "pass": False,
            "checks": {
                "report": False,
                "markdown_claims": False,
            },
            "error": f"报告目录不存在: {report_dir}",
        }

    # 1. check_report
    report_result = run_report_check(str(report_dir))
    report_pass = report_result["pass"]

    # 2. check_markdown_claims (传入 case_id 以加载特殊规则)
    rewrite_json = report_dir / "rewrite_result.json"
    if rewrite_json.exists():
        text = extract_final_markdown(str(rewrite_json))
        watchlist = load_watchlist()
        md_result = run_md_check(text, watchlist, case_id=case_id)
        md_pass = md_result["pass"]
    else:
        md_pass = False
        md_result = {"pass": False, "hits": [], "warnings": []}

    case_pass = report_pass and md_pass

    return {
        "case_id": case_id,
        "pass": case_pass,
        "checks": {
            "report": report_pass,
            "markdown_claims": md_pass,
            "high_risk_sanitizer_count": report_result.get("high_risk_sanitizer_count", 0),
            "high_risk_sanitizer_paths": report_result.get("high_risk_sanitizer_paths", []),
            "needs_manual_review": report_result.get("needs_manual_review", False),
            "terminology_risk_check": report_result.get("terminology_risk_check", "pass"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="运行 mango-doc-writer 回归测试")
    parser.add_argument(
        "--cases",
        nargs="+",
        default=None,
        help="要检查的 case ID 列表（默认: 002 和 009）",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(REPORTS_DIR),
        help="tests/reports 目录路径",
    )
    parser.add_argument(
        "--output",
        default=str(REPORTS_DIR / "regression-summary.json"),
        help="汇总报告输出路径",
    )
    args = parser.parse_args()

    cases = args.cases or DEFAULT_CASES
    reports_dir = Path(args.reports_dir)

    print(f"mango-doc-writer 回归测试")
    print(f"{'=' * 50}")
    print(f"cases: {', '.join(cases)}")
    print(f"reports: {reports_dir}")
    print()

    results = []
    for case_id in cases:
        result = run_single_case(case_id, reports_dir)
        results.append(result)
        icon = "✅" if result["pass"] else "❌"
        r_icon = "✅" if result["checks"]["report"] else "❌"
        m_icon = "✅" if result["checks"]["markdown_claims"] else "❌"
        hr_count = result["checks"].get("high_risk_sanitizer_count", 0)
        hr_note = f" hr_san={hr_count}" if hr_count > 0 else ""
        print(f"  {icon} {case_id:40s} report={r_icon} markdown={m_icon}{hr_note}")

    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    failed = total - passed

    # High-risk sanitizer 汇总
    total_hr_san = sum(r["checks"].get("high_risk_sanitizer_count", 0) for r in results)
    cases_with_hr = [r["case_id"] for r in results if r["checks"].get("high_risk_sanitizer_count", 0) > 0]
    if total_hr_san > 0:
        print(f"\n⚠️ High-Risk Sanitizer: {total_hr_san} fixes in {len(cases_with_hr)} cases")
        for cid in cases_with_hr:
            print(f"   - {cid}")

    summary = {
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "total_high_risk_sanitizer": total_hr_san,
        "cases_with_high_risk_sanitizer": cases_with_hr,
        "cases": results,
    }

    print()
    print(f"{'=' * 50}")
    print(f"总计: {total} | 通过: {passed} | 失败: {failed}")
    print(f"结果: {'✅ ALL PASS' if failed == 0 else '❌ SOME FAILED'}")

    # 写入文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n汇总报告已写入: {output_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
