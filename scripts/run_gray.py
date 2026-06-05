#!/usr/bin/env python3
"""
run_gray.py — 一键灰度模式运行 mango-doc-writer
自动设置 candidate + rerank 环境变量，运行 pipeline，结束后恢复原环境。

用法：
  python scripts/run_gray.py inputs/xxx.json
  python scripts/run_gray.py "粘贴材料文本"
  python scripts/run_gray.py --mode assisted_expansion --doc-type 领导讲话 "材料"
  python scripts/run_gray.py --mode assisted_expansion --style-domain dianguang_siqing --organization-scope jiuzhirun --content-type subsidiary_highlight --doc-type 亮点工作材料 "材料"
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta

VALID_MODES = ["safe_official", "assisted_expansion", "creative_mimic"]

VALID_DOC_TYPES = [
    "新闻稿", "领导讲话", "汇报材料", "亮点工作材料", "请示",
    "函", "通知", "会议纪要", "总结", "通报", "宣传推文",
    "工作方案", "会议新闻", "经营月报", "理论学习发言", "auto",
]

VALID_STYLE_DOMAINS = [
    "dianguang_siqing", "mango_official_account", "official_doc",
    "business_knowledge", "auto",
]

VALID_ORG_SCOPES = [
    "hunan_broadcast_group", "dianguang_media", "mango_excellent_media",
    "subsidiary", "jiuzhirun", "project_company", "auto",
]

VALID_CONTENT_TYPES = [
    "headquarters_update", "subsidiary_update", "subsidiary_highlight",
    "leader_research", "meeting_news", "leader_speech", "event_activity",
    "brand_campaign", "industry_event", "training_activity", "culture_tourism",
    "investment", "ai_training", "honor_award", "project_progress",
    "business_operation", "auto",
]

VALID_LENGTH_MODES = ["short", "standard", "long", "custom"]

# ─── 配置 ─────────────────────────────────────────────────────────────

CANDIDATE_COLLECTION = "mango_style_docs_v020_candidate_rebuild_459"
RERANK_ENABLED = "true"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
RUN_INPUT = os.path.join(SCRIPT_DIR, "run_input.py")
GRAY_USAGE_DIR = os.path.join(PROJECT_DIR, "tests", "reports", "gray-usage")
TEMP_INPUT_DIR = os.path.join(PROJECT_DIR, "inputs", "_gray_temp")

TZ_CN = timezone(timedelta(hours=8))

# ─── 篇幅规则表（style_domain + output_doc_type + content_type → 字数+段落+结构）───

def _M(style, doc, content=None):
    """快捷构造篇幅规则"""
    return {"style": style, "doc": doc, "content": content}

# 核心规则：先匹配 (style, doc, content)，再匹配 (style, doc)，再匹配 (doc)，最后 fallback
_LENGTH_RULES = [
    # ── dianguang_siqing 司情风格 ──
    # 司情普通新闻稿/子公司动态/总部动态：偏短
    (_M("dianguang_siqing", "新闻稿"),
     {"short": {"words": "200-350", "paragraphs": "3-4段", "structure": "导语+主体+结尾"},
      "standard": {"words": "300-600", "paragraphs": "4-5段", "structure": "导语+主体进展+结尾"},
      "long": {"words": "700-1000", "paragraphs": "5-7段", "structure": "充分展开各部分"}}),
    # 司情活动类/文旅/投资/获奖：中等
    (_M("dianguang_siqing", "新闻稿", "event_activity"),
     {"short": {"words": "250-400", "paragraphs": "3-4段", "structure": "导语+活动内容+意义"},
      "standard": {"words": "400-700", "paragraphs": "4-5段", "structure": "导语+活动详情+亮点+意义"},
      "long": {"words": "800-1000", "paragraphs": "5-7段", "structure": "充分展开活动内容"}}),
    (_M("dianguang_siqing", "新闻稿", "culture_tourism"),
     {"short": {"words": "250-400", "paragraphs": "3-4段", "structure": "数据+活动+模式"},
      "standard": {"words": "400-700", "paragraphs": "4-5段", "structure": "数据+活动详情+模式探索+展望"},
      "long": {"words": "800-1000", "paragraphs": "5-7段", "structure": "充分展开"}}),
    (_M("dianguang_siqing", "新闻稿", "honor_award"),
     {"short": {"words": "250-400", "paragraphs": "3-4段", "structure": "获奖+原因+意义"},
      "standard": {"words": "400-700", "paragraphs": "4-5段", "structure": "获奖详情+原因+意义+展望"},
      "long": {"words": "800-1000", "paragraphs": "5-7段", "structure": "充分展开"}}),
    (_M("dianguang_siqing", "新闻稿", "investment"),
     {"short": {"words": "250-400", "paragraphs": "3-4段", "structure": "投资+标的+意义"},
      "standard": {"words": "400-700", "paragraphs": "4-5段", "structure": "投资详情+背景+意义+展望"},
      "long": {"words": "800-1000", "paragraphs": "5-7段", "structure": "充分展开"}}),
    # 司情亮点工作材料：可以更长
    (_M("dianguang_siqing", "亮点工作材料"),
     {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "背景+亮点+成效"},
      "standard": {"words": "600-900", "paragraphs": "4-5段", "structure": "背景+亮点举措+成效+下一步"},
      "long": {"words": "1000-1300", "paragraphs": "5-7段", "structure": "充分展开每个亮点"}}),
    # 司情领导讲话：必须长
    (_M("dianguang_siqing", "领导讲话"),
     {"short": {"words": "800-1000", "paragraphs": "5-7段", "structure": "开场+部署+号召"},
      "standard": {"words": "1200-1800", "paragraphs": "8-12段", "structure": "开场+形势判断+3-5项部署+结尾号召"},
      "long": {"words": "2000以上", "paragraphs": "12段以上", "structure": "每项部署至少2-3句展开"}}),
    # 司情汇报材料：标准公文长度
    (_M("dianguang_siqing", "汇报材料"),
     {"short": {"words": "700-900", "paragraphs": "4-5小节", "structure": "基本情况+进展+问题+下一步"},
      "standard": {"words": "1000-1500", "paragraphs": "5小节", "structure": "基本情况+主要进展+亮点+问题+下一步"},
      "long": {"words": "1800以上", "paragraphs": "5-7小节", "structure": "充分展开"}}),
    # 司情宣传推文
    (_M("dianguang_siqing", "宣传推文"),
     {"short": {"words": "300-500", "paragraphs": "3-4段", "structure": "标题+概要+亮点"},
      "standard": {"words": "500-800", "paragraphs": "4-6段", "structure": "标题+活动详情+亮点+意义"},
      "long": {"words": "900-1200", "paragraphs": "6-8段", "structure": "充分展开"}}),

    # ── mango_official_account 芒果公众号风格 ──
    (_M("mango_official_account", "新闻稿"),
     {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "导语+主体+结尾"},
      "standard": {"words": "700-1000", "paragraphs": "5-7段", "structure": "导语+背景+主体+亮点+结尾"},
      "long": {"words": "1200-1500", "paragraphs": "7-10段", "structure": "充分展开"}}),
    (_M("mango_official_account", "宣传推文"),
     {"short": {"words": "500-700", "paragraphs": "3-4段", "structure": "标题+活动概要+亮点"},
      "standard": {"words": "800-1200", "paragraphs": "5-7段", "structure": "传播性标题+活动现场+亮点表达+意义提升"},
      "long": {"words": "1300-1800", "paragraphs": "7-9段", "structure": "增强现场感和传播节奏"}}),
    (_M("mango_official_account", "领导讲话"),
     {"short": {"words": "1000-1200", "paragraphs": "5-7段", "structure": "开场+部署+号召"},
      "standard": {"words": "1500-2200", "paragraphs": "8-12段", "structure": "充分展开各项部署"},
      "long": {"words": "2500以上", "paragraphs": "12段以上", "structure": "每项部署充分展开"}}),
    (_M("mango_official_account", "新闻稿", "event_activity"),
     {"short": {"words": "500-700", "paragraphs": "3-4段", "structure": "导语+活动+意义"},
      "standard": {"words": "800-1200", "paragraphs": "5-7段", "structure": "导语+活动详情+亮点+意义+展望"},
      "long": {"words": "1300-1800", "paragraphs": "7-9段", "structure": "充分展开"}}),
    (_M("mango_official_account", "新闻稿", "leader_research"),
     {"short": {"words": "500-700", "paragraphs": "3-4段", "structure": "调研+指示+意义"},
      "standard": {"words": "800-1200", "paragraphs": "5-7段", "structure": "调研过程+关注重点+指示要求+意义"},
      "long": {"words": "1300-1800", "paragraphs": "7-9段", "structure": "充分展开"}}),

    # ── official_doc 公文风格 ──
    (_M("official_doc", "汇报材料"),
     {"short": {"words": "700-900", "paragraphs": "4-5小节", "structure": "基本情况+进展+问题+下一步"},
      "standard": {"words": "1000-1500", "paragraphs": "5小节", "structure": "基本情况+主要进展+亮点+问题+下一步"},
      "long": {"words": "1800以上", "paragraphs": "5-7小节", "structure": "充分展开"}}),
    (_M("official_doc", "请示"),
     {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "缘由+事项+结尾"},
      "standard": {"words": "700-1000", "paragraphs": "4-5段", "structure": "缘由+必要性+请示事项+结尾"},
      "long": {"words": "1200-1500", "paragraphs": "5-6段", "structure": "充分说明理由"}}),
    (_M("official_doc", "通知"),
     {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "对象+事项+要求"},
      "standard": {"words": "700-1000", "paragraphs": "4-5段", "structure": "背景+事项+要求+时间节点"},
      "long": {"words": "1200-1500", "paragraphs": "5-6段", "structure": "充分说明"}}),
    (_M("official_doc", "函"),
     {"short": {"words": "400-600", "paragraphs": "3段", "structure": "缘由+事项+结尾"},
      "standard": {"words": "700-1000", "paragraphs": "3-4段", "structure": "缘由+事项+回复要求+结尾"},
      "long": {"words": "1200-1500", "paragraphs": "4-5段", "structure": "充分说明"}}),
    (_M("official_doc", "总结"),
     {"short": {"words": "700-900", "paragraphs": "4-5段", "structure": "工作+成效+问题+计划"},
      "standard": {"words": "1000-1500", "paragraphs": "5-6段", "structure": "充分展开"},
      "long": {"words": "1800以上", "paragraphs": "6-8段", "structure": "全面展开"}}),
    (_M("official_doc", "亮点工作材料"),
     {"short": {"words": "700-900", "paragraphs": "4-5段", "structure": "背景+亮点+成效"},
      "standard": {"words": "1000-1500", "paragraphs": "5-6段", "structure": "背景+亮点+成效+经验+下一步"},
      "long": {"words": "1800以上", "paragraphs": "6-8段", "structure": "充分展开"}}),

    # ── business_knowledge 业务知识 ──
    (_M("business_knowledge", "汇报材料"),
     {"short": {"words": "700-900", "paragraphs": "4-5小节", "structure": "基本情况+进展+问题+下一步"},
      "standard": {"words": "1000-1500", "paragraphs": "5小节", "structure": "充分展开"},
      "long": {"words": "1800以上", "paragraphs": "5-7小节", "structure": "全面展开"}}),

    # ── 通用 fallback（按 doc_type） ──
    (_M("*", "新闻稿"),
     {"short": {"words": "300-500", "paragraphs": "3-4段", "structure": "导语+主体+结尾"},
      "standard": {"words": "500-800", "paragraphs": "4-6段", "structure": "导语+背景+主体+结尾"},
      "long": {"words": "1000-1300", "paragraphs": "6-8段", "structure": "充分展开"}}),
    (_M("*", "领导讲话"),
     {"short": {"words": "800-1000", "paragraphs": "5-7段", "structure": "开场+部署+号召"},
      "standard": {"words": "1200-1800", "paragraphs": "8-12段", "structure": "充分展开各项部署"},
      "long": {"words": "2000以上", "paragraphs": "12段以上", "structure": "每项部署至少2-3句"}}),
    (_M("*", "汇报材料"),
     {"short": {"words": "700-900", "paragraphs": "4-5小节", "structure": "基本情况+进展+问题+下一步"},
      "standard": {"words": "1000-1500", "paragraphs": "5小节", "structure": "充分展开"},
      "long": {"words": "1800以上", "paragraphs": "5-7小节", "structure": "全面展开"}}),
    (_M("*", "亮点工作材料"),
     {"short": {"words": "500-700", "paragraphs": "3-4段", "structure": "背景+亮点+成效"},
      "standard": {"words": "800-1200", "paragraphs": "4-6段", "structure": "背景+亮点+成效+经验+下一步"},
      "long": {"words": "1500以上", "paragraphs": "6-8段", "structure": "充分展开"}}),
    (_M("*", "宣传推文"),
     {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "标题+概要+亮点"},
      "standard": {"words": "700-1000", "paragraphs": "5-7段", "structure": "传播性标题+活动+亮点+意义"},
      "long": {"words": "1200以上", "paragraphs": "7-9段", "structure": "充分展开"}}),
    (_M("*", "新闻稿"),
     {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "导语+主体+结尾"},
      "standard": {"words": "500-800", "paragraphs": "4-6段", "structure": "导语+主体+结尾"},
      "long": {"words": "800-1200", "paragraphs": "6-8段", "structure": "充分展开"}}),
    # 最终 fallback
    (_M("*", "*"),
     {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "核心+展开+结尾"},
      "standard": {"words": "600-900", "paragraphs": "4-6段", "structure": "根据内容组织"},
      "long": {"words": "1000-1500", "paragraphs": "6-10段", "structure": "充分展开"}}),
]

# ─── 风格域 requirement 映射 ──────────────────────────────────────────

_STYLE_DOMAIN_HINTS = {
    "dianguang_siqing": "参考电广传媒司情风格，保持正式、简洁、信息密度高。",
    "mango_official_account": "参考芒果公众号/芒果系公开稿风格，表达更具传播感但保持事实克制。",
    "official_doc": "采用公文风格，结构清楚，语气正式克制。",
    "business_knowledge": "参考业务知识库资料风格，注重事实准确和专业表达。",
    "auto": "根据素材自动判断合适风格。",
}

# ─── 组织范围 requirement 映射 ────────────────────────────────────────

_ORG_SCOPE_HINTS = {
    "hunan_broadcast_group": "稿件主体为湖南广播影视集团/台集团，注意集团口径。",
    "dianguang_media": "稿件主体为电广传媒，注意公司口径。",
    "mango_excellent_media": "稿件主体为芒果超媒，注意芒果超媒口径。",
    "subsidiary": "稿件主体为子公司，注意子公司口径。",
    "jiuzhirun": "稿件主体为久之润/久游网，注意子公司口径。",
    "project_company": "稿件主体为项目公司，注意项目公司口径。",
    "auto": "根据素材自动判断组织主体。",
}

# ─── 内容类型 requirement 映射 ────────────────────────────────────────

_CONTENT_TYPE_HINTS = {
    "headquarters_update": "题材为总部动态，注意总部层面的工作部署和战略方向。",
    "subsidiary_update": "题材为子公司动态，注意子公司的具体工作和进展。",
    "subsidiary_highlight": "题材为子公司亮点工作，注意亮点、成效、经验、下一步。",
    "leader_research": "题材为领导调研，注意调研过程、关注重点、指示要求。",
    "meeting_news": "题材为会议新闻，注意会议时间、参会人员、主要内容、议定事项。",
    "leader_speech": "题材为领导讲话，注意政治站位、形势判断、工作部署、号召动员。",
    "event_activity": "题材为活动类，注意活动时间、地点、参与主体、现场亮点、活动意义。",
    "brand_campaign": "题材为品牌活动/宣传活动，注意品牌亮点、传播效果、受众反馈。",
    "industry_event": "题材为行业活动/论坛/展会，注意行业背景、重要发言、合作成果。",
    "training_activity": "题材为培训活动，注意培训内容、学习要点、应用方向。",
    "culture_tourism": "题材为文旅动态，注意经营数据、活动亮点、模式探索。",
    "investment": "题材为投资动态，注意投资主体、标的、金额、战略意义。",
    "ai_training": "题材为AI培训，注意技术要点、应用场景、业务融合方向。",
    "honor_award": "题材为获奖荣誉，保留正式评价语气，注意获奖原因和意义。",
    "project_progress": "题材为项目进展，注意推进情况、阶段性成果、下一步计划。",
    "business_operation": "题材为经营动态，注意经营数据、增长分析、模式探索。",
    "auto": "根据素材自动判断内容题材。",
}


def save_env():
    return {
        "RAG_COLLECTION_STYLE": os.environ.get("RAG_COLLECTION_STYLE"),
        "RAG_METADATA_RERANK_ENABLED": os.environ.get("RAG_METADATA_RERANK_ENABLED"),
        "DEEPSEEK_MODEL": os.environ.get("DEEPSEEK_MODEL"),
    }


def set_gray_env():
    os.environ["RAG_COLLECTION_STYLE"] = CANDIDATE_COLLECTION
    os.environ["RAG_METADATA_RERANK_ENABLED"] = RERANK_ENABLED


def restore_env(saved):
    for key, val in saved.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


def _get_length_rule(style_domain, output_doc_type, content_type, length_mode, target_words=None):
    """获取完整的篇幅规则（字数+段落+结构），按 style_domain + doc_type + content_type 匹配"""
    if length_mode == "custom" and target_words:
        if target_words <= 600:
            ref_mode = "short"
        elif target_words <= 1200:
            ref_mode = "standard"
        else:
            ref_mode = "long"
        # 找到最匹配的规则作为参考
        ref = _find_matching_rule(style_domain, output_doc_type, content_type)
        ref_rule = ref.get(ref_mode, ref.get("standard", {"words": "600-900", "paragraphs": "4-6段", "structure": "根据内容组织"}))
        return {
            "words": f"目标约 {target_words} 字",
            "paragraphs": ref_rule["paragraphs"],
            "structure": ref_rule["structure"],
        }
    ref = _find_matching_rule(style_domain, output_doc_type, content_type)
    return ref.get(length_mode, ref.get("standard", {"words": "600-900", "paragraphs": "4-6段", "structure": "根据内容组织"}))


def _find_matching_rule(style_domain, output_doc_type, content_type):
    """按优先级匹配规则：(style, doc, content) > (style, doc) > (style, *) > (*, doc) > (*, *)"""
    # 精确匹配
    for matcher, rule in _LENGTH_RULES:
        if (matcher["style"] == style_domain and matcher["doc"] == output_doc_type
                and matcher.get("content") == content_type):
            return rule
    # style + doc
    for matcher, rule in _LENGTH_RULES:
        if (matcher["style"] == style_domain and matcher["doc"] == output_doc_type
                and matcher.get("content") is None):
            return rule
    # style + * (style-specific fallback)
    for matcher, rule in _LENGTH_RULES:
        if matcher["style"] == style_domain and matcher["doc"] == "*":
            return rule
    # * + doc
    for matcher, rule in _LENGTH_RULES:
        if matcher["style"] == "*" and matcher["doc"] == output_doc_type:
            return rule
    # * + *
    for matcher, rule in _LENGTH_RULES:
        if matcher["style"] == "*" and matcher["doc"] == "*":
            return rule
    return {"short": {"words": "400-600", "paragraphs": "3-4段", "structure": "核心+展开"},
            "standard": {"words": "600-900", "paragraphs": "4-6段", "structure": "根据内容组织"},
            "long": {"words": "1000-1500", "paragraphs": "6-10段", "structure": "充分展开"}}


def _build_requirement(mode, style_domain, organization_scope, content_type,
                       output_doc_type, length_mode, target_words=None):
    """根据五字段 + generation_mode 构建完整 requirement"""
    parts = []

    # 1. 扩写模式声明
    if mode == "assisted_expansion":
        parts.append("本次使用 assisted_expansion 可控扩写模式。")
    elif mode == "creative_mimic":
        parts.append("本次为内部灵感稿模式，仅供参考，不可直接正式使用。")

    # 2. 风格要求
    style_hint = _STYLE_DOMAIN_HINTS.get(style_domain, _STYLE_DOMAIN_HINTS["auto"])
    parts.append(style_hint)

    # 3. 组织主体
    org_hint = _ORG_SCOPE_HINTS.get(organization_scope, _ORG_SCOPE_HINTS["auto"])
    parts.append(org_hint)

    # 4. 内容题材
    ct_hint = _CONTENT_TYPE_HINTS.get(content_type, _CONTENT_TYPE_HINTS["auto"])
    parts.append(ct_hint)

    # 5. 输出文体
    doc_base = _DOC_TYPE_BASE_REQUIREMENTS.get(output_doc_type, _DOC_TYPE_BASE_REQUIREMENTS["新闻稿"])
    parts.append(doc_base)

    # 6. 篇幅要求（字数+段落+结构）
    length_rule = _get_length_rule(style_domain, output_doc_type, content_type, length_mode, target_words)
    parts.append(
        f"篇幅要求：{length_rule['words']}字，{length_rule['paragraphs']}。"
        f"结构要求：{length_rule['structure']}。"
    )

    # 7. 内容厚度要求
    parts.append(_get_depth_requirement(style_domain, output_doc_type, content_type))

    # 8. assisted_expansion 扩写规则
    if mode == "assisted_expansion":
        parts.append(
            "扩写规则：\n"
            "- 不允许只把事实流水账排列成短句，每个核心事实至少补充背景承接、动作过程、意义表达中的至少一种；\n"
            "- 可补充正式衔接语、结构层次、工作导向表达；\n"
            "- 可将过于简略的事实点扩展为更完整、自然的正式句式；\n"
            "- 不得编造输入中没有的具体领导姓名、职务、时间、地点、数据、金额、会议结论、奖项来源；\n"
            "- 对模型补充、推断或扩写的内容，必须在人工复核提示中列出；\n"
            "- 输出不是免审正式稿，须经人工确认后使用。"
        )

    return "\n".join(parts)


def _get_depth_requirement(style_domain, output_doc_type, content_type):
    """根据 style_domain + doc_type + content_type 返回内容厚度要求"""
    # 司情短讯类：允许短，信息密度优先
    if style_domain == "dianguang_siqing" and output_doc_type == "新闻稿" and content_type in (
        "headquarters_update", "subsidiary_update", "meeting_news"):
        return (
            "内容要求：司情短讯允许短小精悍，重点是信息密度高、事实准确、结构清楚。"
            "不要为了凑字数加入空泛表达。"
        )
    # 司情活动/文旅/获奖类
    if style_domain == "dianguang_siqing" and output_doc_type == "新闻稿":
        return (
            "内容要求：保持司情正式风格，可以适度展开活动亮点和意义，但不要过度宣传化。"
        )
    depth_rules = {
        "领导讲话": (
            "内容厚度要求：工作部署不能全部单句化，每个'一是、二是、三是'后至少有2句展开。"
            "如果素材只给关键词，可在不编造具体事实的前提下补充工作逻辑、推进要求、责任落实表达。"
            "所有补充内容必须进入人工复核提示。"
        ),
        "宣传推文": (
            "内容厚度要求：要有传播感，不要写成流水账。"
            "至少包含活动现场描写、亮点表达、意义提升。"
        ),
        "汇报材料": (
            "内容厚度要求：不要只有标题式小节，每个小节必须至少有事实描述+分析判断。"
            "如果缺数据，要写'数据待补充/需人工确认'，不能编造。"
        ),
        "亮点工作材料": (
            "内容厚度要求：每个亮点至少展开2-3句，包含具体做法、取得成效、经验启示。"
            "不要只写'取得了良好成效'一句带过。"
        ),
    }
    return depth_rules.get(output_doc_type, (
        "内容要求：不要只写流水账，每个核心事实至少补充背景承接、动作过程、意义表达中的至少一种。"
    ))


# 文种 → 基础 requirement 映射（向后兼容）
_DOC_TYPE_BASE_REQUIREMENTS = {
    "新闻稿": "最终成稿为新闻稿，正式、有传播感，适合对外发布。",
    "领导讲话": "最终成稿为领导讲话稿，体现政治站位、工作部署和号召动员，语气庄重有力。",
    "汇报材料": "最终成稿为汇报材料，突出工作进展、亮点成效、问题分析和下一步思路。",
    "亮点工作材料": "最终成稿为亮点工作材料，突出亮点、成效、经验，适合内部展示或上级汇报。",
    "通知": "最终成稿为通知，语言直接清楚，明确对象、事项、时间和要求。",
    "请示": "最终成稿为请示，一文一事，理由清楚，结尾使用妥否请批示。",
    "报告": "最终成稿为报告，重点汇报情况、进展、问题和建议，不夹带请示事项。",
    "函": "最终成稿为函，语气平实，用于平级或不相隶属单位沟通事项。",
    "总结": "最终成稿为工作总结，包含工作开展情况、主要成效、经验做法、存在问题和下一步计划。",
    "会议纪要": "最终成稿为会议纪要，记录会议事项、议定事项和责任分工。",
    "通报": "最终成稿为通报，事实准确、表述客观，不夸大。",
    "宣传推文": "最终成稿为宣传推文/公众号推文，表达有传播感，适合新媒体发布。",
    "auto": "根据内容自动判断合适文种。",
}


def generate_temp_input(text, mode="safe_official", doc_type=None,
                        style_domain="auto", organization_scope="auto",
                        content_type="auto", length_mode="standard",
                        target_words=None):
    """从粘贴文本生成临时 input json"""
    os.makedirs(TEMP_INPUT_DIR, exist_ok=True)
    ts = datetime.now(TZ_CN).strftime("%Y%m%d_%H%M%S")
    filename = f"gray_{ts}.json"
    filepath = os.path.join(TEMP_INPUT_DIR, filename)

    # 确定 effective doc_type
    if doc_type is None:
        effective_doc_type = "新闻稿"
    elif doc_type == "auto":
        effective_doc_type = None
    else:
        effective_doc_type = doc_type

    requirement = _build_requirement(
        mode, style_domain, organization_scope, content_type,
        effective_doc_type or "auto", length_mode, target_words
    )

    input_data = {
        "requirement": requirement,
        "draft": text,
        "generation_mode": mode,
        "style_domain": style_domain,
        "organization_scope": organization_scope,
        "content_type": content_type,
        "length_mode": length_mode,
    }
    if effective_doc_type:
        input_data["specified_doc_type"] = effective_doc_type
    if target_words:
        input_data["target_words"] = target_words

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(input_data, f, ensure_ascii=False, indent=2)

    return filepath


def _count_chinese_chars(text):
    """近似计算中文字符数（含中文标点）"""
    import re
    return len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text))


def find_latest_output():
    outputs_dir = os.path.join(PROJECT_DIR, "outputs")
    if not os.path.exists(outputs_dir):
        return None
    dirs = sorted(
        [d for d in os.listdir(outputs_dir) if d.startswith("2026")],
        reverse=True,
    )
    return os.path.join(outputs_dir, dirs[0]) if dirs else None


def read_pipeline_report(output_dir):
    report_path = os.path.join(output_dir, "pipeline_report.json")
    if not os.path.exists(report_path):
        return {}
    with open(report_path, encoding="utf-8") as f:
        return json.load(f)


def generate_gray_record(input_file, report, output_dir, mode="safe_official",
                         doc_type_source="default", requested_doc_type=None,
                         style_domain="auto", organization_scope="auto",
                         content_type="auto", length_mode="standard",
                         target_words=None, requested_model="default",
                         model_override_enabled=False, elapsed_seconds=0):
    """生成灰度记录"""
    os.makedirs(GRAY_USAGE_DIR, exist_ok=True)
    ts = datetime.now(TZ_CN).strftime("%Y%m%d_%H%M%S")
    record_path = os.path.join(GRAY_USAGE_DIR, f"gray-record-{ts}.md")

    qg_scores = report.get("final_quality_scores", {})
    qg_pass = report.get("quality_gate_pass")
    has_expansion_report = bool(report.get("expansion_report_summary"))
    has_expansion_review = bool(report.get("expansion_review_summary"))
    has_expansion_quality = bool(report.get("expansion_quality_summary"))
    has_draft_disclaimer = bool(report.get("draft_disclaimer"))
    report_official_use = report.get("official_use_allowed")
    report_gen_mode = report.get("generation_mode", mode)
    classified_doc_type = report.get("doc_type", "unknown")

    # 获取篇幅规则
    length_rule = _get_length_rule(style_domain, requested_doc_type or "auto", content_type, length_mode, target_words)
    expected_word_range = length_rule["words"]
    expected_min_paragraphs = length_rule["paragraphs"]

    # 计算 actual_word_count 和 actual_paragraph_count
    actual_word_count = 0
    actual_paragraph_count = 0
    fm_path = os.path.join(output_dir, "final_markdown.md") if output_dir else None
    if fm_path and os.path.exists(fm_path):
        with open(fm_path, encoding="utf-8") as f:
            fm_text = f.read()
        actual_word_count = _count_chinese_chars(fm_text)
        # 计算段落数（非空行数）
        actual_paragraph_count = len([l for l in fm_text.split('\n') if l.strip()])

    # 判断篇幅是否达标
    # 从 expected_word_range 提取下限数字
    try:
        range_str = expected_word_range.replace('目标约 ', '').replace(' 字', '').replace('以上', '-99999')
        lower_bound = int(range_str.split('-')[0])
        length_under_target = actual_word_count > 0 and actual_word_count < lower_bound * 0.7
    except (ValueError, IndexError):
        length_under_target = False

    # 段落数判断
    try:
        min_para = int(expected_min_paragraphs.split('-')[0].replace('段', '').replace('小节', '').replace('以上', ''))
        para_under_target = actual_paragraph_count > 0 and actual_paragraph_count < min_para
    except (ValueError, IndexError):
        para_under_target = False

    length_under_target = length_under_target or para_under_target

    under_reason = ""
    if length_under_target:
        reasons = []
        if actual_word_count > 0:
            try:
                if actual_word_count < lower_bound * 0.7:
                    reasons.append(f"字数{actual_word_count}低于目标下限{lower_bound}的70%")
            except:
                pass
        if para_under_target:
            reasons.append(f"段落数{actual_paragraph_count}低于目标{expected_min_paragraphs}")
        under_reason = "，".join(reasons) if reasons else "篇幅不达标"

    # requirement 摘要
    req_summary = ""
    try:
        req_path = input_file  # input_file 可能就是临时文件路径
        if os.path.exists(req_path):
            with open(req_path, encoding="utf-8") as f:
                req_data = json.load(f)
            req_summary = req_data.get("requirement", "")[:300]
    except:
        pass

    content = f"""# Gray Usage Record — {datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M")}

## 五字段任务拆解
- requested_style_domain：{style_domain}
- requested_organization_scope：{organization_scope}
- requested_content_type：{content_type}
- requested_output_doc_type：{requested_doc_type or '(未指定)'}
- requested_length_mode：{length_mode}
- target_words：{target_words or '(未指定)'}
- doc_type_source：{doc_type_source}
- classified_doc_type：{classified_doc_type}

## 篇幅控制
- expected_word_range：{expected_word_range}
- expected_min_paragraphs：{expected_min_paragraphs}
- actual_word_count：{actual_word_count} 字
- actual_paragraph_count：{actual_paragraph_count}
- length_under_target：{"⚠️ 是" if length_under_target else "✅ 否"}
- length_under_target_reason：{under_reason or 'N/A'}

## 模型配置
- requested_model：{requested_model}
- effective_model：{report.get('default_model', requested_model)}
- model_override_enabled：{"✅" if model_override_enabled else "❌"}
- elapsed_seconds：{elapsed_seconds:.1f}s

## 基本信息
- 日期：{datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M")}
- 输入文件：{input_file}
- generation_mode：{mode}
- official_use_allowed（mode 判断）：{mode != 'creative_mimic'}

## requirement 摘要
{req_summary}...

## 运行结果
- Pipeline status：{report.get("status", "unknown")}
- final_markdown 是否生成：{"✅" if fm_path and os.path.exists(fm_path) else "❌"}
- QG pass/fail：{"✅ pass" if qg_pass else "❌ fail" if qg_pass is False else "unknown"}
- QG 各维度分数：{json.dumps(qg_scores, ensure_ascii=False)}
- RAG primary：{report.get("rag_primary_collection", "unknown")}
- rag_collections_used：{json.dumps(report.get("rag_collections_used", []), ensure_ascii=False)}
- generation_mode（report）：{report_gen_mode}
- official_use_allowed（report）：{report_official_use}
- expansion_report_summary：{"✅" if has_expansion_report else "❌"}
- expansion_review_summary：{"✅" if has_expansion_review else "❌"}
- expansion_quality_summary：{"✅" if has_expansion_quality else "❌"}
- draft_disclaimer：{"✅" if has_draft_disclaimer else "❌"}

## 人工评价
- 是否采用：（待填写）
- 风格匹配度 1-5：（待填写）
- 结构匹配度 1-5：（待填写）
- 篇幅合适度 1-5：（待填写）
- 事实安全性 1-5：（待填写）
- 主要修改点：（待填写）

## 结论
- 本次是否支持继续灰度：（待填写）
- 是否发现 bug：（待填写）
"""

    with open(record_path, "w", encoding="utf-8") as f:
        f.write(content)

    return record_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="一键灰度模式运行 mango-doc-writer（五字段任务拆解）",
        usage="python scripts/run_gray.py [--mode] [--style-domain] [--organization-scope] [--content-type] [--doc-type] [--length] INPUT"
    )
    parser.add_argument("input", help="input json 文件路径或粘贴材料文本")
    parser.add_argument("--stdout", action="store_true", help="输出到 stdout")
    parser.add_argument("--mode", choices=VALID_MODES, default="safe_official",
                        help=f"generation_mode (默认: safe_official)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="pipeline 超时秒数 (默认: 300)")
    parser.add_argument("--style-domain", choices=VALID_STYLE_DOMAINS, default="auto",
                        help="风格域 (默认: auto)")
    parser.add_argument("--organization-scope", choices=VALID_ORG_SCOPES, default="auto",
                        help="组织范围 (默认: auto)")
    parser.add_argument("--content-type", choices=VALID_CONTENT_TYPES, default="auto",
                        help="内容类型 (默认: auto)")
    parser.add_argument("--doc-type", choices=VALID_DOC_TYPES, default=None,
                        help="输出文体 (默认: 新闻稿)")
    parser.add_argument("--length", choices=VALID_LENGTH_MODES, default="standard",
                        help="篇幅模式 (默认: standard)")
    parser.add_argument("--target-words", type=int, default=None,
                        help="自定义目标字数 (--length custom 时使用)")
    parser.add_argument("--model", default=None,
                        help="临时覆盖模型 (如 deepseek-v4-pro，默认使用 .env 配置)")
    return parser.parse_args()


def main():
    args = parse_args()
    arg = args.input
    mode = args.mode
    stdout_mode = args.stdout

    # 五字段
    style_domain = args.style_domain
    organization_scope = args.organization_scope
    content_type = args.content_type
    doc_type_arg = args.doc_type
    length_mode = args.length
    target_words = args.target_words

    doc_type_source = "default"
    requested_doc_type = None

    # ─── 输入处理 ────────────────────────────────────────────────────

    if os.path.exists(arg):
        input_file = arg
        with open(input_file, encoding="utf-8") as f:
            input_data = json.load(f)
        original_mode = input_data.get("generation_mode")
        if "--mode" in sys.argv and mode != "safe_official":
            print(f"[gray] 覆盖 generation_mode: {original_mode or '(unset)'} → {mode}")
        elif original_mode:
            mode = original_mode

        # 五字段覆盖
        if doc_type_arg is not None:
            doc_type_source = "user_specified"
            requested_doc_type = doc_type_arg
        else:
            doc_type_source = "input_file"
            requested_doc_type = input_data.get("specified_doc_type")

        # 构建 requirement 并写入临时文件
        effective_doc_type = doc_type_arg if doc_type_arg and doc_type_arg != "auto" else input_data.get("specified_doc_type", "新闻稿")
        input_data["requirement"] = _build_requirement(
            mode, style_domain, organization_scope, content_type,
            effective_doc_type or "auto", length_mode, target_words
        )
        input_data["style_domain"] = style_domain
        input_data["organization_scope"] = organization_scope
        input_data["content_type"] = content_type
        input_data["length_mode"] = length_mode
        if doc_type_arg and doc_type_arg != "auto":
            input_data["specified_doc_type"] = doc_type_arg
        if target_words:
            input_data["target_words"] = target_words

        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', dir=TEMP_INPUT_DIR, delete=False, encoding='utf-8'
        )
        json.dump(input_data, tmp, ensure_ascii=False, indent=2)
        tmp.close()
        input_file = tmp.name
        print(f"[gray] 临时输入文件: {input_file}")

    else:
        print("检测到粘贴文本，自动生成临时 input json...")
        if doc_type_arg is not None:
            if doc_type_arg == "auto":
                doc_type_source = "auto"
                requested_doc_type = "auto"
            else:
                doc_type_source = "user_specified"
                requested_doc_type = doc_type_arg
        else:
            doc_type_source = "default"
            requested_doc_type = "新闻稿"
        input_file = generate_temp_input(
            arg, mode, doc_type_arg, style_domain, organization_scope,
            content_type, length_mode, target_words
        )
        print(f"生成: {input_file}")

    # 打印任务拆解
    print(f"[gray] 五字段任务拆解:")
    print(f"  style_domain: {style_domain}")
    print(f"  organization_scope: {organization_scope}")
    print(f"  content_type: {content_type}")
    print(f"  output_doc_type: {requested_doc_type or '新闻稿'}")
    print(f"  length_mode: {length_mode}" + (f" (target={target_words})" if target_words else ""))

    # ─── 保存环境并运行 ─────────────────────────────────────────────

    saved_env = save_env()
    print(f"[gray] 保存环境: RAG_COLLECTION_STYLE={saved_env['RAG_COLLECTION_STYLE'] or '(unset)'}")

    # 模型覆盖
    model_override = args.model
    model_restore_status = "not_needed"
    if model_override:
        os.environ["DEEPSEEK_MODEL"] = model_override
        model_restore_status = "overridden"
        print(f"[gray] 模型覆盖: DEEPSEEK_MODEL={model_override}")

    try:
        set_gray_env()
        print(f"[gray] 灰度模式: collection={CANDIDATE_COLLECTION}, rerank={RERANK_ENABLED}")
        print(f"[gray] generation_mode: {mode}")
        timeout = args.timeout
        print(f"[gray] timeout: {timeout}s")

        cmd = ["python3", RUN_INPUT, input_file]
        if stdout_mode:
            cmd.append("--stdout")

        print(f"[gray] 运行: {' '.join(cmd)}")
        start = time.time()
        result = subprocess.run(cmd, cwd=PROJECT_DIR, timeout=timeout)
        elapsed = time.time() - start

        output_dir = find_latest_output()
        report = read_pipeline_report(output_dir) if output_dir else {}

        # 汇报
        qg_pass = report.get("quality_gate_pass")
        print(f"\n{'='*50}")
        print(f"[gray] Pipeline: {report.get('status', 'unknown')} ({elapsed:.0f}s)")
        print(f"[gray] RAG primary: {report.get('rag_primary_collection', 'unknown')}")
        print(f"[gray] QG: {'pass' if qg_pass else 'fail' if qg_pass is False else 'unknown'}")
        print(f"[gray] 文种: {report.get('doc_type', 'unknown')}")
        print(f"[gray] generation_mode: {report.get('generation_mode', 'unknown')}")

        # 灰度记录
        record_path = generate_gray_record(
            input_file, report, output_dir, mode, doc_type_source, requested_doc_type,
            style_domain, organization_scope, content_type, length_mode, target_words,
            requested_model=model_override or "default",
            model_override_enabled=bool(model_override),
            elapsed_seconds=elapsed,
        )
        print(f"[gray] 灰度记录: {record_path}")

    except subprocess.TimeoutExpired:
        print(f"[gray] ❌ Pipeline 超时 ({timeout}s)")
        model_restore_status = "timeout"
    except Exception as e:
        print(f"[gray] ❌ 错误: {e}")
        model_restore_status = "error"
    finally:
        # 恢复 DEEPSEEK_MODEL
        if model_override:
            original_model = saved_env.get("DEEPSEEK_MODEL")
            if original_model is None:
                os.environ.pop("DEEPSEEK_MODEL", None)
            else:
                os.environ["DEEPSEEK_MODEL"] = original_model
            model_restore_status = "restored"
            print(f"[gray] 模型已恢复: DEEPSEEK_MODEL={os.environ.get('DEEPSEEK_MODEL', '(unset)')}")
        restore_env(saved_env)
        print(f"[gray] 环境已恢复: RAG_COLLECTION_STYLE={os.environ.get('RAG_COLLECTION_STYLE', '(unset)')}")


if __name__ == "__main__":
    main()
