"""
input_parser.py — 将用户输入解析为 PipelineInput

支持两类输入：
1. 结构化 JSON（直接映射）
2. 自然语言（轻量解析，不补事实、不做文种判断）
"""

import json
import re
from typing import Any, Dict, Optional


# 文种关键词 → 可提取的 specified_doc_type
DOC_TYPE_HINTS = {
    "新闻稿": "新闻稿",
    "新闻": "新闻稿",
    "请示": "请示",
    "报告": "报告",
    "通知": "通知",
    "函": "函",
    "通报": "通报",
    "总结": "总结",
    "讲话": "领导讲话",
    "会议纪要": "会议纪要",
    "汇报材料": "汇报材料",
    "汇报": "汇报材料",
}

# 主送单位关键词 → 可提取的 target_unit
TARGET_HINTS = {
    "集团": "集团",
    "总部": "总部",
    "公司": "公司",
    "领导": "领导",
}


def parse_structured_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """解析结构化 JSON 输入"""
    return {
        "requirement": data.get("requirement", ""),
        "draft": data.get("draft", ""),
        "specified_doc_type": data.get("specified_doc_type"),
        "target_unit": data.get("target_unit"),
        "scene": data.get("scene"),
        "output_formats": data.get("output_formats", ["markdown"]),
    }


def parse_natural_language(text: str) -> Dict[str, Any]:
    """解析自然语言输入

    规则：
    - requirement：提取用户要求（冒号/换行前的描述句）
    - draft：提取素材正文（冒号/换行后的内容）
    - specified_doc_type：根据显式文种关键词提取
    - target_unit：根据"报集团""给总部"等提取
    - scene：根据"对外发布""内部汇报"等提取
    """
    text = text.strip()
    requirement = ""
    draft = ""
    specified_doc_type = None
    target_unit = None
    scene = None

    # 分离 requirement 和 draft
    # 模式1："请把下面素材写成XXX：\n素材内容"
    # 模式2："素材内容"（无明确分隔）
    separators = [
        r"[：:]\s*\n",
        r"[：:]\s*",
        r"素材[：:]",
        r"内容[：:]",
        r"如下[：:]",
        r"以下[：:]",
    ]
    for sep in separators:
        parts = re.split(sep, text, maxsplit=1)
        if len(parts) == 2 and len(parts[1].strip()) > 20:
            requirement = parts[0].strip()
            draft = parts[1].strip()
            break

    if not draft:
        # 无法分隔，整段作为 draft
        draft = text
        requirement = "请整理成稿"

    # 提取文种
    for hint, doc_type in DOC_TYPE_HINTS.items():
        if hint in requirement or hint in text[:50]:
            specified_doc_type = doc_type
            break

    # 提取主送单位
    for hint, unit in TARGET_HINTS.items():
        if f"报{hint}" in text or f"给{hint}" in text or f"向{hint}" in text:
            target_unit = unit
            break

    # 提取场景
    scene_keywords = {
        "对外发布": ["对外发布", "对外宣传", "公开发布"],
        "内部汇报": ["内部汇报", "向领导汇报", "工作汇报"],
        "会议发言": ["会议发言", "会上讲话", "工作推进会"],
    }
    for scene_name, keywords in scene_keywords.items():
        if any(kw in text for kw in keywords):
            scene = scene_name
            break

    return {
        "requirement": requirement,
        "draft": draft,
        "specified_doc_type": specified_doc_type,
        "target_unit": target_unit,
        "scene": scene,
        "output_formats": ["markdown"],
    }


def parse_input(raw_input: Any) -> Dict[str, Any]:
    """自动判断输入类型并解析"""
    if isinstance(raw_input, dict):
        return parse_structured_input(raw_input)

    if isinstance(raw_input, str):
        # 尝试解析为 JSON
        try:
            data = json.loads(raw_input)
            if isinstance(data, dict):
                return parse_structured_input(data)
        except json.JSONDecodeError:
            pass
        # 作为自然语言处理
        return parse_natural_language(raw_input)

    raise ValueError(f"不支持的输入类型: {type(raw_input)}")
