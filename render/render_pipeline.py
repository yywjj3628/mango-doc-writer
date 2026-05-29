#!/usr/bin/env python3
"""
render_pipeline.py — 将 final_markdown 接入 typeset-engine 生成 DOCX/PDF。

Markdown-first 策略：
- 所有文种必须输出 final_markdown.md
- 公文类（请示/报告/通知/函/通报）默认生成 DOCX
- 非公文类仅在用户明确要求时生成 DOCX
- 排版失败不影响 final_markdown

用法：
  from render_pipeline import render_case
  result = render_case(case_id, report_dir, output_formats=None)
"""

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

MODULE_DIR = Path(__file__).parent
MAPPING_PATH = MODULE_DIR / "doc_type_mapping.yaml"
TYPESET_API = "http://localhost:9090"


def load_doc_type_mapping():
    """加载文种→排版模板映射。"""
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("doc_type_mapping", {})


def markdown_to_sections(md_text):
    """
    将 Markdown 文本转换为 typeset-engine 的 sections JSON 格式。
    不修改任何事实内容，只做格式转换。
    """
    sections = []
    lines = md_text.split("\n")
    current_section = None
    current_content = []

    for line in lines:
        heading_match = re.match(r'^(#{1,4})\s+(.+)', line)
        if heading_match:
            if current_section:
                current_section["content"] = "\n".join(current_content).strip()
                sections.append(current_section)
                current_content = []
            title = heading_match.group(2).strip()
            current_section = {"type": "heading", "title": title, "content": ""}
        else:
            current_content.append(line)

    if current_section:
        current_section["content"] = "\n".join(current_content).strip()
        sections.append(current_section)
    elif current_content:
        sections.append({
            "type": "heading",
            "title": "正文",
            "content": "\n".join(current_content).strip(),
        })

    return sections


def build_typeset_json(doc_type, title, sections, theme, author="", date=""):
    """构建 typeset-engine API 所需的 JSON。"""
    return {
        "title": title or f"{doc_type}文件",
        "author": author or "",
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "theme": theme,
        "toc": False,
        "sections": sections,
    }


def call_typeset_engine(json_data, output_path, endpoint="/render/docx"):
    """调用 typeset-engine HTTP API。"""
    import urllib.request
    import urllib.error

    url = f"{TYPESET_API}{endpoint}"
    payload = json.dumps(json_data, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
            return True, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def _determine_formats(doc_type, mapping, user_formats):
    """
    确定实际输出格式。

    逻辑：
    1. Markdown 始终输出
    2. 公文类（default_docx=true）默认输出 DOCX
    3. 非公文类仅在用户明确要求时输出 DOCX
    4. 用户明确指定格式时以用户为准
    """
    type_config = mapping.get(doc_type, {})
    default_docx = type_config.get("default_docx", False)

    if user_formats is not None:
        # 用户明确指定了格式
        formats = list(user_formats)
        if "markdown" not in formats:
            formats.insert(0, "markdown")
        reason = "user requested docx" if "docx" in formats else "user requested formats"
        return formats, reason

    # 用户未指定，按策略决定
    formats = ["markdown"]
    if default_docx:
        formats.append("docx")
        reason = "official document default docx"
    else:
        reason = "default markdown-first"

    return formats, reason


def render_case(case_id, report_dir, output_formats=None):
    """
    对单个 case 执行排版。

    Args:
        case_id: Case ID
        report_dir: 报告目录路径
        output_formats: 输出格式列表（None=按策略自动决定）

    Returns:
        dict: 渲染结果
    """
    report_dir = Path(report_dir)
    rewrite_path = report_dir / "rewrite_result.json"
    md_path = report_dir / "final_markdown.md"
    render_dir = report_dir / "render"
    render_dir.mkdir(exist_ok=True)

    # 1. 读取 rewrite_result
    if not rewrite_path.exists():
        return _error_result(case_id, "file_not_found", f"rewrite_result.json 不存在: {rewrite_path}")

    with open(rewrite_path, "r", encoding="utf-8") as f:
        rewrite_result = json.load(f)

    # 2. 读取 final_markdown
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            final_markdown = f.read()
    else:
        final_markdown = rewrite_result.get("final_markdown", "")
        if final_markdown:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(final_markdown)

    if not final_markdown.strip():
        return _error_result(case_id, "empty_markdown", "final_markdown.md 为空")

    # 3. 获取文种和排版配置
    doc_type = rewrite_result.get("doc_type", "其他")
    mapping = load_doc_type_mapping()
    type_config = mapping.get(doc_type, {})
    template = type_config.get("template", "official_document")
    theme = type_config.get("theme", "cms")

    # 4. 确定输出格式（Markdown-first 策略）
    formats, reason = _determine_formats(doc_type, mapping, output_formats)

    # 5. 复制 final_markdown 到 render 目录（始终执行）
    md_copy = render_dir / "final.md"
    with open(md_copy, "w", encoding="utf-8") as f:
        f.write(final_markdown)

    outputs = {"markdown": str(md_copy), "docx": None, "pdf": None}
    warnings = []
    docx_generated = False

    # 6. 调用 typeset-engine（仅当格式包含 docx/pdf 时）
    needs_typeset = any(f in formats for f in ("docx", "pdf"))
    if needs_typeset:
        # 提取标题
        title = ""
        for line in final_markdown.split("\n"):
            m = re.match(r'^#\s+(.+)', line)
            if m:
                title = m.group(1).strip()
                break

        sections = markdown_to_sections(final_markdown)
        typeset_json = build_typeset_json(doc_type, title, sections, theme)

        # 保存调试 JSON
        json_path = render_dir / "typeset_input.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(typeset_json, f, ensure_ascii=False, indent=2)

        for fmt in formats:
            if fmt == "docx":
                docx_path = render_dir / "final.docx"
                ok, err = call_typeset_engine(typeset_json, str(docx_path), "/render/docx")
                if ok:
                    outputs["docx"] = str(docx_path)
                    docx_generated = True
                else:
                    warnings.append(f"DOCX 生成失败: {err}")
            elif fmt == "pdf":
                pdf_path = render_dir / "final.pdf"
                ok, err = call_typeset_engine(typeset_json, str(pdf_path), "/render/pdf")
                if ok:
                    outputs["pdf"] = str(pdf_path)
                else:
                    warnings.append(f"PDF 生成失败: {err}")

    # 7. 确定 render_mode
    if not needs_typeset:
        render_mode = "markdown_only"
    elif docx_generated:
        render_mode = "optional_docx" if not type_config.get("default_docx") else "markdown_first"
    else:
        render_mode = "markdown_only"

    # 8. 生成 render_report
    render_report = {
        "render_mode": render_mode,
        "template_used": template,
        "theme": theme,
        "final_markdown_preserved": True,
        "body_modified": False,
        "facts_added": False,
        "docx_generated": docx_generated,
        "reason": reason,
        "warnings": warnings,
    }

    report_path = render_dir / "render_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(render_report, f, ensure_ascii=False, indent=2)

    status = "success" if not warnings else "partial"
    if not needs_typeset:
        status = "markdown_only"

    return {
        "status": status,
        "case_id": case_id,
        "doc_type": doc_type,
        "outputs": outputs,
        "render_report": render_report,
    }


def _error_result(case_id, error_type, error_message):
    """返回错误结果。"""
    return {
        "status": "failed",
        "case_id": case_id,
        "error_type": error_type,
        "error_message": error_message,
        "fallback": "final_markdown preserved",
        "outputs": {"markdown": None, "docx": None, "pdf": None},
    }
