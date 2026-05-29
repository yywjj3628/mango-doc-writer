"""
schema_prompt.py — 从 JSON Schema 自动生成约束提示

根据阶段名加载对应 schema，提取 enum、required、常见易错字段，
生成简短约束文本注入 system prompt，提高 DeepSeek 输出的 schema 合规率。

不修改 schema 文件，只在调用前追加约束提示。
"""

import json
import os

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS_DIR = os.path.join(SKILL_DIR, "schemas")

SCHEMA_FILES = {
    "classify": "classify.schema.json",
    "extract": "extract.schema.json",
    "plan": "plan.schema.json",
    "draft": "draft.schema.json",
    "review": "review.schema.json",
    "rewrite": "rewrite.schema.json",
    "quality_score": "quality_score.schema.json",
}


def _load_schema(stage_name: str) -> dict:
    filename = SCHEMA_FILES.get(stage_name)
    if not filename:
        return {}
    filepath = os.path.join(SCHEMAS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_enums(schema: dict, path: str = "") -> list:
    """递归收集所有 enum 约束"""
    enums = []
    if not isinstance(schema, dict):
        return enums

    if "enum" in schema:
        enums.append({
            "path": path or "(root)",
            "values": schema["enum"],
        })

    if "properties" in schema:
        for key, val in schema["properties"].items():
            enums.extend(_collect_enums(val, f"{path}.{key}" if path else key))

    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        items = schema["items"]
        if "properties" in items:
            for key, val in items["properties"].items():
                enums.extend(_collect_enums(val, f"{path}[].{key}" if path else f"[].{key}"))

    if "$defs" in schema:
        for key, val in schema["$defs"].items():
            enums.extend(_collect_enums(val, f"$defs.{key}"))

    return enums


def _collect_required(schema: dict, path: str = "") -> list:
    """递归收集所有 required 字段"""
    required = []
    if not isinstance(schema, dict):
        return required

    if "required" in schema:
        required.append({
            "path": path or "(root)",
            "fields": schema["required"],
        })

    if "properties" in schema:
        for key, val in schema["properties"].items():
            required.extend(_collect_required(val, f"{path}.{key}" if path else key))

    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        required.extend(_collect_required(schema["items"], f"{path}[]" if path else "[]"))

    if "$defs" in schema:
        for key, val in schema["$defs"].items():
            required.extend(_collect_required(val, f"$defs.{key}"))

    return required


def _find_string_fields(schema: dict, path: str = "") -> list:
    """找出 type=string 且没有 enum 的叶子字段（这些不允许 null）"""
    fields = []
    if not isinstance(schema, dict):
        return fields

    if schema.get("type") == "string" and "enum" not in schema:
        fields.append(path or "(root)")

    if "properties" in schema:
        for key, val in schema["properties"].items():
            fields.extend(_find_string_fields(val, f"{path}.{key}" if path else key))

    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        items = schema["items"]
        if "properties" in items:
            for key, val in items["properties"].items():
                fields.extend(_find_string_fields(val, f"{path}[].{key}" if path else f"[].{key}"))

    return fields


def build_schema_guard(stage_name: str) -> str:
    """
    根据阶段名生成 schema 约束提示文本。

    输出注入 system prompt，提醒模型遵守 schema 约束。
    """
    schema = _load_schema(stage_name)
    if not schema:
        return ""

    lines = [
        "【Schema 约束 — 必须严格遵守】",
        f"阶段: {stage_name}",
        f"additionalProperties: {'false — 不得输出 schema 未定义的字段' if schema.get('additionalProperties') is False else '未限制'}",
    ]

    # enum 约束
    enums = _collect_enums(schema)
    if enums:
        lines.append("")
        lines.append("enum 字段（必须使用允许值，不得自造）：")
        for e in enums:
            values_str = " / ".join(str(v) for v in e["values"])
            lines.append(f"  - {e['path']}: {values_str}")

    # required 字段
    required = _collect_required(schema)
    if required:
        lines.append("")
        lines.append("required 字段（不得遗漏）：")
        for r in required[:3]:  # 只列前3层，避免太长
            if r["fields"]:
                lines.append(f"  - {r['path']}: {', '.join(r['fields'])}")

    # string 字段不能为 null
    string_fields = _find_string_fields(schema)
    if string_fields:
        lines.append("")
        lines.append("string 字段（不得输出 null，至少输出空字符串 \"\"）：")
        for f in string_fields[:20]:  # 限制数量
            lines.append(f"  - {f}")

    # 常见易错提醒
    lines.append("")
    lines.append("常见易错提醒：")
    lines.append("  - 所有 string 类型字段不得为 null，无内容时用 \"\"")
    lines.append("  - 所有 array 类型字段不得为 null，无内容时用 []")
    lines.append("  - 不得遗漏任何 required 字段")
    lines.append("  - 不得输出 schema 未定义的额外字段")
    lines.append("  - boolean 字段必须是 true 或 false，不得用字符串")

    return "\n".join(lines)
