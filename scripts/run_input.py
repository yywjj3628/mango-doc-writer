#!/usr/bin/env python3
"""
run_input.py — 真实输入运行入口

支持：
  python scripts/run_input.py inputs/example.json
  echo '{...}' | python scripts/run_input.py --stdin
  python scripts/run_input.py inputs/example.json --stdout
  python scripts/run_input.py inputs/example.json --output-dir outputs/custom
  python scripts/run_input.py inputs/example.json --format markdown,docx

用法:
  python scripts/run_input.py <input.json> [options]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 确保项目路径在 sys.path 中
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from pipeline_types import PipelineInput
from input_parser import parse_input
from run_pipeline import run_pipeline, save_results
from output_formatter import format_output, format_user_text


def load_env():
    """从 .env 文件加载环境变量"""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key not in os.environ:
                        os.environ[key] = value.strip()


def run(raw_input, output_dir=None, output_formats=None, stdout_mode=False):
    """运行单篇输入"""
    load_env()

    # 解析输入
    parsed = parse_input(raw_input)

    # 构建 PipelineInput（v0.1.4: 传入 generation_mode）
    pipeline_input = PipelineInput(
        requirement=parsed.get("requirement", ""),
        draft=parsed.get("draft", ""),
        specified_doc_type=parsed.get("specified_doc_type"),
        target_unit=parsed.get("target_unit"),
        scene=parsed.get("scene"),
        generation_mode=parsed.get("generation_mode", "safe_official"),
        # J2.6C.2F: 五字段传递
        style_domain=parsed.get("style_domain"),
        organization_scope=parsed.get("organization_scope"),
        content_type=parsed.get("content_type"),
        output_doc_type=parsed.get("output_doc_type"),
        length_mode=parsed.get("length_mode"),
    )

    # generation_mode 警告提示
    gen_warnings = parsed.get("generation_mode_warnings", [])
    if gen_warnings:
        for w in gen_warnings:
            print(f"  ⚠️ {w}")

    # 输出目录
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_output = str(PROJECT_ROOT / "outputs" / ts)
    out_dir = output_dir or default_output
    os.makedirs(out_dir, exist_ok=True)

    # 运行 pipeline
    start = time.time()
    print(f"🚀 运行 pipeline...")
    print(f"  需求: {pipeline_input.requirement[:80]}...")
    if pipeline_input.draft:
        print(f"  初稿: {pipeline_input.draft[:80]}...")
    print(f"  输出: {out_dir}")
    print()

    result = run_pipeline(pipeline_input)

    # 保存结果
    save_results(out_dir, result)

    # 格式化输出
    formatted = format_output(result, out_dir)

    if stdout_mode:
        # stdout 模式：输出 JSON 到 stdout
        output = {
            "status": formatted["status"],
            "doc_type": formatted["doc_type"],
            "final_markdown_path": formatted["output_files"]["markdown"],
            "docx_path": formatted["output_files"]["docx"],
            "manual_confirmation_count": formatted["summary"]["manual_confirmation_count"],
            "remaining_risk_count": formatted["summary"]["remaining_risk_count"],
            "high_risk_sanitizer": formatted["summary"]["high_risk_sanitizer"],
            "elapsed_seconds": round(time.time() - start, 1),
            "fallback_count": formatted["summary"]["fallback_count"],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 默认模式：输出用户可读文本
        print(format_user_text(formatted))

        # 简要摘要
        summary = formatted["summary"]
        elapsed = round(time.time() - start, 1)
        print(f"\n---")
        print(f"耗时: {elapsed}s | RAG: {summary['rag_status']} | 模型: {summary['default_model']}")
        print(f"输出目录: {out_dir}")

    return formatted


def main():
    parser = argparse.ArgumentParser(description="运行单篇真实输入")
    parser.add_argument("input_file", nargs="?", help="输入 JSON 文件路径")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取输入")
    parser.add_argument("--output-dir", "-o", help="自定义输出目录")
    parser.add_argument("--stdout", action="store_true", help="输出 JSON 到 stdout（简化）")
    parser.add_argument("--format", default="markdown", help="输出格式: markdown, docx, markdown,docx")
    args = parser.parse_args()

    # 读取输入
    raw_input = None
    if args.stdin:
        raw_input = json.load(sys.stdin)
    elif args.input_file:
        if not os.path.exists(args.input_file):
            print(f"❌ 文件不存在: {args.input_file}", file=sys.stderr)
            sys.exit(1)
        with open(args.input_file, "r", encoding="utf-8") as f:
            raw_input = json.load(f)
    else:
        parser.print_help()
        sys.exit(1)

    formats = [f.strip() for f in args.format.split(",")]

    result = run(raw_input, output_dir=args.output_dir, output_formats=formats, stdout_mode=args.stdout)
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
