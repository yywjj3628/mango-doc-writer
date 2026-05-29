"""
运行单个测试 case

用法：
    python scripts/run_case.py tests/cases/002-fake-report-real-request.md
"""

import json
import os
import re
import sys

# 确保 pipeline 目录在 path 中
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SKILL_DIR, "pipeline"))

from pipeline_types import PipelineInput
from run_pipeline import run_pipeline, save_results


def parse_case_file(filepath: str) -> dict:
    """
    解析测试 case Markdown 文件，提取用户需求和用户初稿。

    Args:
        filepath: case 文件路径

    Returns:
        {"requirement": ..., "draft": ...}
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取"用户需求"和"用户初稿"章节内容
    sections = {}
    current_key = None
    current_lines = []

    for line in content.split("\n"):
        # 匹配 ## 级别标题
        if re.match(r"^##\s+用户需求", line.strip()):
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = "requirement"
            current_lines = []
        elif re.match(r"^##\s+用户初稿", line.strip()):
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = "draft"
            current_lines = []
        elif re.match(r"^##\s+", line.strip()) and current_key:
            # 遇到下一个 ## 级别标题，结束当前章节
            sections[current_key] = "\n".join(current_lines).strip()
            current_key = None
            current_lines = []
        elif current_key:
            current_lines.append(line)

    # 处理最后一个章节
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/run_case.py <case_file_path>")
        print("示例: python scripts/run_case.py tests/cases/002-fake-report-real-request.md")
        sys.exit(1)

    case_path = sys.argv[1]

    if not os.path.exists(case_path):
        print(f"错误: 文件不存在 — {case_path}")
        sys.exit(1)

    # 解析 case
    print(f"📋 解析 case: {case_path}")
    sections = parse_case_file(case_path)

    requirement = sections.get("requirement", "")
    draft = sections.get("draft", "")

    if not requirement:
        print("❌ 未找到「用户需求」章节")
        sys.exit(1)
    if not draft:
        print("❌ 未找到「用户初稿」章节")
        sys.exit(1)

    print(f"  需求: {requirement[:50]}...")
    print(f"  初稿: {draft[:50]}...")

    # 构造输入
    input_data = PipelineInput(
        requirement=requirement,
        draft=draft,
    )

    # 运行 pipeline
    print(f"\n🚀 运行 pipeline...")
    result = run_pipeline(input_data)

    # 确定输出目录
    case_filename = os.path.splitext(os.path.basename(case_path))[0]
    output_dir = os.path.join(SKILL_DIR, "tests", "reports", case_filename)

    # 保存结果
    saved_files = save_results(output_dir, result)

    # 输出结果
    print(f"\n📊 状态: {result.status}")

    if result.status == "success":
        print(f"  文种: {result.pipeline_report.doc_type}")
        print(f"  风险: {result.pipeline_report.risk_level}")
        print(f"  Review 通过: {result.pipeline_report.review_pass}")
        print(f"  需 Rewrite: {result.pipeline_report.rewrite_required}")
        print(f"  人工确认项: {result.pipeline_report.manual_confirmation_count}")
        print(f"  剩余风险: {result.pipeline_report.remaining_risk_count}")
        print(f"  Final markdown: {len(result.final_markdown or '')} 字符")
    elif result.status == "skipped":
        print(f"  原因: {result.error}")
        print(f"  (模型调用器未接入，case 标记为 skipped)")
    else:
        print(f"  失败阶段: {result.failed_stage}")
        print(f"  错误: {result.error}")

    print(f"\n📁 输出目录: {output_dir}")
    print(f"  保存文件: {len(saved_files)} 个")

    return result


if __name__ == "__main__":
    main()
