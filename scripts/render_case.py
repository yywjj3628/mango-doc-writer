#!/usr/bin/env python3
"""
render_case.py — 单 case 排版 CLI。

用法：
  python scripts/render_case.py tests/reports/002-fake-report-real-request --format docx
  python scripts/render_case.py tests/reports/001-news --format docx pdf
  python scripts/render_case.py tests/reports/005-meeting-minutes
"""

import argparse
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "render"))

from render_pipeline import render_case


def main():
    parser = argparse.ArgumentParser(description="mango-doc-writer 单 case 排版")
    parser.add_argument("report_dir", help="tests/reports/<case_id> 目录路径")
    parser.add_argument(
        "--format", nargs="+", default=None,
        choices=["markdown", "docx", "pdf"],
        help="输出格式（默认按文种策略自动决定）",
    )
    parser.add_argument(
        "--case-id", default=None,
        help="Case ID（默认从目录名推断）",
    )
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    if not report_dir.is_dir():
        print(f"错误: 目录不存在: {report_dir}", file=sys.stderr)
        sys.exit(1)

    case_id = args.case_id or report_dir.name
    # output_formats=None 让 render_pipeline 按策略自动决定
    output_formats = args.format

    print(f"mango-doc-writer 排版")
    print(f"{'=' * 50}")
    print(f"case: {case_id}")
    print(f"formats: {'auto (Markdown-first 策略)' if output_formats is None else ', '.join(output_formats)}")
    print(f"report: {report_dir}")
    print()

    result = render_case(case_id, str(report_dir), output_formats)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "success":
        print(f"\n✅ 排版成功")
        for fmt, path in result.get("outputs", {}).items():
            if path:
                print(f"  {fmt}: {path}")
    elif result["status"] == "partial":
        print(f"\n⚠️ 部分成功")
        for fmt, path in result.get("outputs", {}).items():
            if path:
                print(f"  {fmt}: {path}")
        for w in result.get("render_report", {}).get("warnings", []):
            print(f"  ⚠️ {w}")
    else:
        print(f"\n❌ 排版失败: {result.get('error_message', 'unknown')}")
        print(f"  fallback: {result.get('fallback', 'N/A')}")

    sys.exit(0 if result["status"] in ("success", "partial") else 1)


if __name__ == "__main__":
    main()
