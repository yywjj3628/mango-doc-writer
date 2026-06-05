#!/usr/bin/env python3
"""
久之润经营月报 Lite 版生成脚本

用法：
  python3 scripts/run_monthly_report_lite.py inputs/example-monthly-report-lite.json
  python3 scripts/run_monthly_report_lite.py --input inputs/example-monthly-report-lite.json

功能：
  - 读取并校验 Schema
  - 读取固定模板
  - 根据输入决定显示或隐藏章节
  - 生成需要的分析段落
  - 确定性渲染最终 Markdown
  - 执行数字追溯检查
  - 输出报告和最终 Markdown
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "references" / "templates" / "jiuzhirun-monthly-report-lite.md"
SCHEMA_PATH = PROJECT_ROOT / "references" / "schemas" / "jiuzhirun-monthly-report-lite.schema.json"

TZ_CN = timezone(timedelta(hours=8))


def load_template() -> str:
    """加载固定模板"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_schema() -> dict:
    """加载 Schema"""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_input(data: dict, schema: dict) -> list:
    """校验输入是否满足 Schema 要求"""
    errors = []
    required = schema.get("required", [])
    for field in required:
        if field not in data or not data[field]:
            errors.append(f"缺少必填字段: {field}")
    return errors


def extract_report_month(reporting_period: str) -> str:
    """从报告期间提取月份"""
    match = re.search(r"(\d+)月", reporting_period)
    if match:
        return f"{match.group(1)}月"
    return ""


def render_template(template: str, data: dict) -> str:
    """确定性渲染模板"""
    result = template

    # 基础变量替换
    result = result.replace("{{reporting_period}}", data.get("reporting_period", ""))
    result = result.replace("{{report_month}}", extract_report_month(data.get("reporting_period", "")))
    result = result.replace("{{report_date}}", data.get("report_date", "【日期待确认】"))

    # 分析段落：有事实则生成占位标记，无事实则保留表格占位但不生成分析
    analysis_fields = {
        "monthly_revenue_analysis_facts": "monthly_revenue_analysis",
        "cumulative_analysis_facts": "cumulative_revenue_analysis",
        "balance_sheet_analysis_facts": "balance_sheet_analysis",
        "cash_flow_analysis_facts": "cash_flow_analysis",
    }

    for facts_field, placeholder in analysis_fields.items():
        if data.get(facts_field):
            result = result.replace("{{" + placeholder + "}}", f"{{{{generate:{placeholder}}}}}")
        else:
            result = result.replace("{{" + placeholder + "}}", f"（{placeholder.replace('_', ' ')}待财务数据补充）")

    # 工作内容
    result = result.replace("{{monthly_work_narrative}}", data.get("monthly_work_facts", "（待补充）"))
    result = result.replace("{{next_month_plan_narrative}}", data.get("next_month_plan", "（待补充）"))

    # 问题与风险：未提供时隐藏整个章节
    if data.get("issues_and_risks"):
        result = result.replace("{{issues_and_risks_narrative}}", data["issues_and_risks"])
    else:
        # 删除整个"三、问题与风险"章节
        result = re.sub(r"## 三、问题与风险\n.*?(?=\n## 四|\n---|\Z)", "", result, flags=re.DOTALL)

    return result


def check_number_tracing(final_md: str, input_data: dict) -> dict:
    """数字追溯检查"""
    # 收集输入中的所有数字
    input_text = json.dumps(input_data, ensure_ascii=False)
    input_numbers = set(re.findall(r"\d[\d,.]*", input_text))

    # 收集输出中的所有数字
    output_numbers = set(re.findall(r"\d[\d,.]*", final_md))

    # 排除日期、章节序号等
    excluded_patterns = [
        r"^\d{4}$",  # 年份
        r"^\d{1,2}$",  # 月份/日期
        r"^[一二三四五六七八九十]+$",  # 中文序号
    ]

    untraced = []
    for num in output_numbers:
        if any(re.match(p, num) for p in excluded_patterns):
            continue
        if num not in input_numbers:
            untraced.append(num)

    return {
        "total_numbers_in_output": len(output_numbers),
        "traced_numbers": len(output_numbers) - len(untraced),
        "untraced_numbers": untraced,
        "validation_passed": len(untraced) == 0,
    }


def generate_report(input_data: dict, final_md: str, validation: dict, tracing: dict) -> dict:
    """生成报告"""
    return {
        "status": "success",
        "report_type": "jiuzhirun_monthly_report_lite",
        "reporting_period": input_data.get("reporting_period"),
        "template_source": str(TEMPLATE_PATH),
        "input_fields_used": list(input_data.keys()),
        "validation": validation,
        "number_tracing": tracing,
        "output_path": None,  # 由调用者设置
        "generated_at": datetime.now(TZ_CN).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="久之润经营月报 Lite 版生成")
    parser.add_argument("input", nargs="?", help="输入 JSON 文件路径")
    parser.add_argument("--input", dest="input_alt", help="输入 JSON 文件路径")
    parser.add_argument("--output", help="输出目录")
    args = parser.parse_args()

    input_path = args.input or args.input_alt
    if not input_path:
        print("❌ 请提供输入 JSON 文件路径")
        sys.exit(1)

    # 加载输入
    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    # 加载 Schema
    schema = load_schema()

    # 校验输入
    errors = validate_input(input_data, schema)
    if errors:
        print("❌ 输入校验失败:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # 加载模板
    template = load_template()

    # 渲染模板
    final_md = render_template(template, input_data)

    # 数字追溯检查
    tracing = check_number_tracing(final_md, input_data)

    # 生成报告
    validation = {"input_valid": True, "missing_fields": []}
    report = generate_report(input_data, final_md, validation, tracing)

    # 输出
    ts = datetime.now(TZ_CN).strftime("%Y%m%d-%H%M%S")
    output_dir = args.output or str(PROJECT_ROOT / "outputs" / f"monthly-lite-{ts}")
    os.makedirs(output_dir, exist_ok=True)

    # 保存 final_markdown
    md_path = os.path.join(output_dir, "final_markdown.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    # 保存报告
    report["output_path"] = md_path
    report_path = os.path.join(output_dir, "pipeline_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 输出摘要
    print(f"✅ 经营月报 Lite 版生成成功")
    print(f"  输出: {md_path}")
    print(f"  报告: {report_path}")
    print(f"  数字追溯: {tracing['traced_numbers']}/{tracing['total_numbers_in_output']} 可追溯")
    if tracing["untraced_numbers"]:
        print(f"  ⚠️ 无法追溯数字: {tracing['untraced_numbers']}")


if __name__ == "__main__":
    main()
