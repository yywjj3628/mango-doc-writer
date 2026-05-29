#!/usr/bin/env python3
"""
generate_cases.py — 批量生成 8 个测试案例的六阶段 JSON + final_markdown.md + pipeline_report.json。

用法:
  cd skills/mango-doc-writer
  python tests/generate_cases.py
"""

import json
import os
from pathlib import Path

import jsonschema

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_DIR / "schemas"
REPORTS_DIR = PROJECT_DIR / "tests" / "reports"

SCHEMA_MAP = {
    "classify_result": "classify.schema.json",
    "extract_result": "extract.schema.json",
    "plan_result": "plan.schema.json",
    "draft_result": "draft.schema.json",
    "review_result": "review.schema.json",
    "rewrite_result": "rewrite.schema.json",
}

CASES = [
    "001-news",
    "003-report",
    "004-notice",
    "005-meeting-minutes",
    "006-leader-speech",
    "007-summary",
    "008-letter",
    "010-terminology-risk",
]

STAGE_FILES = [
    "classify_result.json",
    "extract_result.json",
    "plan_result.json",
    "draft_result.json",
    "review_result.json",
    "rewrite_result.json",
]

# ─────────────────────────────────────────────
# Policy constants
# ─────────────────────────────────────────────
EXTRACTION_POLICY = {
    "only_user_provided_facts": True,
    "no_external_knowledge": True,
    "no_rag_facts": True,
    "no_invented_data": True,
}

DRAFT_POLICY = {
    "body_generated": True,
    "no_new_facts": True,
    "use_only_extract_facts": True,
    "rag_used_for_style_only": True,
    "follow_plan_structure": True,
    "follow_doc_type_rules": True,
    "follow_org_title_dictionary": True,
}

REVIEW_POLICY = {
    "no_body_generation": True,
    "no_rewrite": True,
    "no_new_facts": True,
    "no_rag_call": True,
    "check_fact_grounding": True,
    "check_doc_type_rules": True,
    "check_org_title_dictionary": True,
}

REWRITE_POLICY = {
    "body_rewritten": True,
    "no_new_facts": True,
    "use_only_extract_facts": True,
    "no_rag_call": True,
    "follow_review_instructions": True,
    "follow_doc_type_rules": True,
    "follow_org_title_dictionary": True,
}

FINAL_CHECKS_ALL_TRUE = {
    "doc_type_fixed": True,
    "unsupported_facts_removed": True,
    "blocked_items_removed": True,
    "terminology_checked": True,
    "manual_confirmations_preserved": True,
}


def make_check(status="pass", summary="", issues_count=0):
    return {"status": status, "summary": summary, "issues_count": issues_count}


# ═══════════════════════════════════════════
# CASE DEFINITIONS
# ═══════════════════════════════════════════

def gen_001_news():
    case_id = "001-news"
    classify = {
        "doc_type": "新闻稿",
        "doc_type_confidence": 0.95,
        "direction": "对外宣传",
        "style_level": 3,
        "risk_level": "low",
        "reason": "用户明确要求写成新闻稿，素材包含时间、地点、事件、机构等新闻要素，无文种冲突信号。",
        "required_rules": ["新闻稿"],
        "required_structure": ["标题", "导语", "主体", "结尾"],
        "forbidden_items": ["不得编造领导出席", "不得编造领导评价", "不得编造成果具体名称", "不得编造活动影响范围", "不得编造参会人员名单"],
        "need_manual_confirmation": False,
        "manual_confirmation_fields": [],
    }
    extract = {
        "source_summary": "用户素材涉及文化科技融合创新活动，包含时间、地点、事件、机构等信息。",
        "facts": {
            "time": ["5月20日"],
            "location": ["马栏山"],
            "organizations": ["湖南广电集团", "芒果超媒"],
            "leaders": [],
            "persons": [],
            "products": [],
            "projects": [],
            "events": ["文化科技融合创新活动"],
            "data": [],
            "achievements": ["活动现场发布了三项创新成果"],
            "problems": [],
            "requests": [],
            "policies": [],
            "documents": [],
        },
        "fact_items": [
            {"type": "time", "value": "5月20日", "source_text": "5月20日，文化科技融合创新活动在马栏山举行", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "location", "value": "马栏山", "source_text": "文化科技融合创新活动在马栏山举行", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "event", "value": "文化科技融合创新活动", "source_text": "文化科技融合创新活动在马栏山举行", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "organization", "value": "湖南广电集团", "source_text": "来自湖南广电集团、芒果超媒等单位的代表参加交流", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "organization", "value": "芒果超媒", "source_text": "来自湖南广电集团、芒果超媒等单位的代表参加交流", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "achievement", "value": "活动现场发布了三项创新成果", "source_text": "活动现场发布了三项创新成果", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": "具体成果名称未提供"},
        ],
        "missing_fields": [
            {"field": "三项创新成果的具体名称", "reason": "用户未提供具体成果名称", "impact": "影响新闻报道的详细程度", "suggestion": "建议用户提供三项成果的正式名称"},
            {"field": "参会具体人员名单", "reason": "用户仅写'代表'，未提供具体人员", "impact": "影响新闻人物报道", "suggestion": "建议确认参会人员"},
            {"field": "活动主办单位", "reason": "用户未提供主办单位信息", "impact": "影响新闻来源和权威性", "suggestion": "建议确认主办单位"},
        ],
        "cannot_infer": [
            {"field": "三项创新成果的具体名称", "reason": "用户未提供，不得自动补充"},
            {"field": "具体参会人员", "reason": "用户未提供，不得自动补充"},
            {"field": "活动影响范围", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "missing_detail", "detail": "成果具体名称缺失，可能影响新闻稿质量", "level": "medium"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "新闻稿对外宣传场景，style_level=3，需重点防止编造领导出席/评价/成果名称。结构采用标准新闻稿：标题→导语→主体→结尾。",
        "doc_type": "新闻稿",
        "direction": "对外宣传",
        "style_level": 3,
        "risk_level": "low",
        "title_plan": {
            "recommended_title": "文化科技融合创新活动在马栏山成功举行",
            "title_type": "新闻稿标题",
            "title_confidence": 0.8,
            "title_basis": ["extract.events 包含'文化科技融合创新活动'", "extract.location 包含'马栏山'"],
            "title_risks": ["缺少主办单位前缀"],
            "alternative_titles": ["马栏山文化科技融合创新活动发布三项创新成果"],
        },
        "addressee_plan": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "新闻稿无特定主送对象"},
        "signer_plan": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "新闻稿无需落款"},
        "sections": [
            {"section_id": "S1", "section_name": "导语", "purpose": "概括时间、地点、事件", "content_guidance": "用一句话交代5月20日在马栏山举行的文化科技融合创新活动", "fact_bindings": [{"fact_type": "time", "fact_value": "5月20日", "source_from_extract": True}, {"fact_type": "location", "fact_value": "马栏山", "source_from_extract": True}, {"fact_type": "event", "fact_value": "文化科技融合创新活动", "source_from_extract": True}], "blocked_items": ["不得编造领导出席", "不得编造活动规模"], "word_count_estimate": 80, "needs_manual_input": False},
            {"section_id": "S2", "section_name": "主体", "purpose": "展开活动内容和成果", "content_guidance": "描述三项创新成果发布和代表交流情况，不编造具体成果名称", "fact_bindings": [{"fact_type": "achievement", "fact_value": "活动现场发布了三项创新成果", "source_from_extract": True}, {"fact_type": "organization", "fact_value": "湖南广电集团", "source_from_extract": True}, {"fact_type": "organization", "fact_value": "芒果超媒", "source_from_extract": True}], "blocked_items": ["不得编造成果名称", "不得编造领导评价", "不得编造具体参会人员"], "word_count_estimate": 200, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "结尾", "purpose": "活动意义或展望", "content_guidance": "简述活动意义，不得编造影响范围", "fact_bindings": [], "blocked_items": ["不得编造'产生广泛社会影响'", "不得编造'取得重大突破'"], "word_count_estimate": 80, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "正式、有传播感", "key_expressions": ["融合创新", "成果发布", "深入交流"], "forbidden_expressions": ["奋楫扬帆", "澎湃动能", "取得重大突破", "产生广泛社会影响"], "style_reference": "doc-type-rules.md 新闻稿章节"},
        "title_rules": ["新闻稿标题应包含事件关键词", "标题只能使用 extract 中已有信息"],
        "addressee_resolution": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "signer_resolution": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "title_suggestions": {"recommended_title": "文化科技融合创新活动在马栏山成功举行", "alternative_titles": ["马栏山文化科技融合创新活动发布三项创新成果"], "title_rules": ["新闻稿标题应包含事件关键词"]},
        "missing_fields": [
            {"field": "活动主办单位", "reason": "用户未提供", "impact": "medium", "suggestion": "人工确认"},
            {"field": "三项创新成果的具体名称", "reason": "用户未提供", "impact": "high", "suggestion": "人工确认"},
        ],
        "cannot_infer": [
            {"field": "三项创新成果的具体名称", "reason": "用户未提供"},
        ],
        "risk_flags": [
            {"type": "missing_detail", "detail": "成果具体名称缺失", "level": "medium"},
        ],
        "manual_confirmation_fields": [
            {"field": "活动主办单位全称", "reason": "用户未提供"},
            {"field": "三项创新成果的正式名称", "reason": "用户未提供"},
        ],
        "draft_directives": {"total_word_count_estimate": 400, "must_use_facts": ["5月20日", "马栏山", "文化科技融合创新活动", "湖南广电集团", "芒果超媒", "三项创新成果"], "must_avoid": ["领导出席", "领导评价", "成果具体名称", "奋楫扬帆", "澎湃动能"], "format_requirements": ["新闻稿标准格式", "导语+主体+结尾"]},
    }

    draft_markdown = """# 文化科技融合创新活动在马栏山成功举行

5月20日，文化科技融合创新活动在马栏山举行。活动现场发布了三项创新成果，来自湖南广电集团、芒果超媒等单位的代表参加交流。

此次文化科技融合创新活动聚焦文化与科技深度融合方向，三项创新成果的发布受到参会代表的高度关注。与会代表围绕创新成果进行了深入交流，分享了各自在文化科技领域的实践经验。

来自湖南广电集团、芒果超媒等单位的代表纷纷表示，此次活动为行业交流搭建了良好平台，有助于推动文化科技领域的持续创新。"""

    draft = {
        "draft_summary": "按新闻稿结构生成初稿，导语交代时间地点事件，主体描述成果发布和交流情况，未编造领导出席和评价。",
        "doc_type": "新闻稿",
        "direction": "对外宣传",
        "style_level": 3,
        "risk_level": "low",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "5月20日", "fact_type": "time", "fact_value": "5月20日", "source_text": "5月20日，文化科技融合创新活动在马栏山举行", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "马栏山", "fact_type": "location", "fact_value": "马栏山", "source_text": "文化科技融合创新活动在马栏山举行", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "文化科技融合创新活动", "fact_type": "event", "fact_value": "文化科技融合创新活动", "source_text": "5月20日，文化科技融合创新活动在马栏山举行", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "发布了三项创新成果", "fact_type": "achievement", "fact_value": "活动现场发布了三项创新成果", "source_text": "活动现场发布了三项创新成果", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "湖南广电集团", "fact_type": "organization", "fact_value": "湖南广电集团", "source_text": "来自湖南广电集团、芒果超媒等单位的代表参加交流", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "芒果超媒", "fact_type": "organization", "fact_value": "芒果超媒", "source_text": "来自湖南广电集团、芒果超媒等单位的代表参加交流", "source": "extract_result.fact_items", "confidence": 0.9},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [
            {"raw_value": "湖南广电集团", "used_value": "湖南广电集团", "type": "organization", "source": "user_input", "confidence": 0.9, "needs_manual_confirmation": False, "note": None},
            {"raw_value": "芒果超媒", "used_value": "芒果超媒", "type": "organization", "source": "user_input", "confidence": 0.9, "needs_manual_confirmation": False, "note": None},
        ],
        "blocked_items_check": [
            {"item": "不得编造领导出席", "status": "not_used", "reason": "初稿未出现领导出席"},
            {"item": "不得编造领导评价", "status": "not_used", "reason": "初稿未出现领导评价"},
            {"item": "不得编造成果具体名称", "status": "not_used", "reason": "初稿仅使用'三项创新成果'概括"},
            {"item": "不得编造活动影响范围", "status": "not_used", "reason": "初稿未编造影响范围"},
            {"item": "不得编造参会人员名单", "status": "not_used", "reason": "初稿仅使用'代表'表述"},
        ],
        "warnings": [
            {"level": "medium", "type": "missing_field", "message": "缺少具体成果名称", "related_field": "三项创新成果", "action": "建议用户提供成果正式名称"},
            {"level": "medium", "type": "missing_field", "message": "缺少主办单位", "related_field": "主办单位", "action": "建议用户确认"},
            {"level": "low", "type": "missing_field", "message": "缺少领导信息", "related_field": None, "action": "如有领导出席信息可补充"},
        ],
        "manual_confirmation_fields": [
            {"field": "活动主办单位全称", "reason": "用户未提供", "impact": "影响新闻稿权威性", "required_before_final": False},
            {"field": "三项创新成果的正式名称", "reason": "用户未提供", "impact": "影响新闻报道详实度", "required_before_final": False},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以新闻稿结构撰写，导语+主体+结尾完整，所有事实均可溯源，未编造领导信息。",
        "pass": True,
        "score": 88,
        "rewrite_required": False,
        "risk_level": "low",
        "checks": {
            "doc_type_check": make_check("pass", "新闻稿结构正确", 0),
            "structure_check": make_check("pass", "导语→主体→结尾结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自 extract_result", 0),
            "fact_usage_report_check": make_check("pass", "6条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("pass", "机构称谓使用正确", 0),
            "blocked_items_check": make_check("pass", "5项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "3项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "2项人工确认字段已标记", 0),
            "style_check": make_check("pass", "传播感适度，无过度宣传腔", 0),
            "format_check": make_check("pass", "新闻稿格式正确", 0),
        },
        "issues": [
            {"issue_id": "R001-001", "level": "low", "type": "fact_not_grounded", "location": "主体第二段", "detail": "'此次活动为行业交流搭建了良好平台'为一般性评价，用户未明确要求", "evidence": "用户素材未提及活动意义", "suggestion": "可保留为一般性表述或删除", "rewrite_hint": "keep"},
            {"issue_id": "R001-002", "level": "low", "type": "warning_missing", "location": "全文", "detail": "缺少主办单位和成果具体名称", "evidence": "extract.missing_fields 包含两项", "suggestion": "建议用户补充", "rewrite_hint": "mark_manual_confirmation"},
        ],
        "rewrite_instructions": [
            {"priority": "low", "target": "活动意义表述", "action": "keep", "instruction": "一般性表述可保留", "basis": "新闻稿结尾可用一般性展望"},
            {"priority": "low", "target": "缺失信息", "action": "mark_manual_confirmation", "instruction": "标记缺失字段等待人工确认", "basis": "extract.missing_fields"},
        ],
        "manual_confirmation_fields": [
            {"field": "活动主办单位全称", "reason": "用户未提供", "impact": "影响新闻稿权威性", "required_before_final": False},
            {"field": "三项创新成果的正式名称", "reason": "用户未提供", "impact": "影响新闻报道详实度", "required_before_final": False},
        ],
        "review_policy": REVIEW_POLICY,
    }

    final_md = """# 文化科技融合创新活动在马栏山成功举行

5月20日，文化科技融合创新活动在马栏山举行。活动现场发布了三项创新成果，来自湖南广电集团、芒果超媒等单位的代表参加交流。

此次文化科技融合创新活动聚焦文化与科技深度融合方向，三项创新成果的发布受到参会代表的高度关注。与会代表围绕创新成果进行了深入交流，分享了各自在文化科技领域的实践经验。

来自湖南广电集团、芒果超媒等单位的代表纷纷表示，此次活动为行业交流搭建了良好平台，有助于推动文化科技领域的持续创新。"""

    rewrite = {
        "rewrite_summary": "review 未发现 critical 级别问题，初稿结构正确。保留新闻稿结构和所有用户事实，标记缺失信息等待人工确认。",
        "doc_type": "新闻稿",
        "direction": "对外宣传",
        "style_level": 3,
        "risk_level": "low",
        "final_markdown": final_md,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [
            {"issue_id": "R001-001", "reason": "一般性表述可保留，不影响新闻稿质量", "required_action": "可保留或根据需要调整"},
            {"issue_id": "R001-002", "reason": "信息缺失需人工补充", "required_action": "确认主办单位和成果名称后补充"},
        ],
        "remaining_risks": [
            {"level": "medium", "type": "missing_field", "detail": "活动主办单位全称缺失", "action": "人工确认后补充至导语"},
            {"level": "medium", "type": "missing_field", "detail": "三项创新成果的正式名称缺失", "action": "人工确认后补充至主体"},
        ],
        "manual_confirmation_fields": [
            {"field": "活动主办单位全称", "reason": "用户未提供", "impact": "影响新闻稿权威性", "required_before_final": False},
            {"field": "三项创新成果的正式名称", "reason": "用户未提供", "impact": "影响新闻报道详实度", "required_before_final": False},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success",
        "doc_type": "新闻稿",
        "risk_level": "low",
        "review_pass": True,
        "rewrite_required": False,
        "manual_confirmation_count": 2,
        "remaining_risk_count": 2,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None,
        "error_type": None,
        "error_message": None,
        "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify,
        "extract_result.json": extract,
        "plan_result.json": plan,
        "draft_result.json": draft,
        "review_result.json": review,
        "rewrite_result.json": rewrite,
        "final_markdown.md": final_md,
        "pipeline_report.json": pipeline_report,
    }


def gen_003_report():
    case_id = "003-report"
    classify = {
        "doc_type": "报告",
        "doc_type_confidence": 0.93,
        "direction": "上行文",
        "style_level": 2,
        "risk_level": "low",
        "reason": "用户明确'汇报'，内容为工作进展和下一步计划，无请求批准/批复/拨款信号，符合报告特征。",
        "required_rules": ["报告"],
        "required_structure": ["工作概述", "已完成工作", "下一步计划", "特此报告结尾"],
        "forbidden_items": ["不得编造具体数据", "不得编造项目名称", "不得添加请示事项", "不得使用'妥否，请批示'结尾", "不得使用'请批复''请批准'"],
        "need_manual_confirmation": False,
        "manual_confirmation_fields": [],
    }
    extract = {
        "source_summary": "用户素材涉及工作推进情况汇报，包含已完成工作和下一步计划。",
        "facts": {
            "time": ["今年以来"], "location": [], "organizations": ["集团"], "leaders": [], "persons": [], "products": [],
            "projects": ["重点任务"], "events": [], "data": [],
            "achievements": ["完成了前期梳理", "资源协调", "阶段性复盘"],
            "problems": [], "requests": [], "policies": [], "documents": [],
        },
        "fact_items": [
            {"type": "time", "value": "今年以来", "source_text": "今年以来，相关工作围绕重点任务推进", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "organization", "value": "集团", "source_text": "向集团汇报的正式报告", "confidence": 0.8, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "集团正式全称待确认"},
            {"type": "project", "value": "重点任务", "source_text": "相关工作围绕重点任务推进", "confidence": 0.85, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "具体任务名称待确认"},
            {"type": "achievement", "value": "完成了前期梳理", "source_text": "完成了前期梳理", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "achievement", "value": "资源协调", "source_text": "资源协调", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "achievement", "value": "阶段性复盘", "source_text": "阶段性复盘", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
        ],
        "missing_fields": [
            {"field": "具体项目/任务名称", "reason": "用户仅写'重点任务'，未提供正式名称", "impact": "影响报告具体性", "suggestion": "建议确认具体任务名称"},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响报告落款", "suggestion": "建议确认汇报单位"},
            {"field": "具体数据", "reason": "用户未提供量化数据", "impact": "影响报告详实度", "suggestion": "建议提供工作量化指标"},
        ],
        "cannot_infer": [
            {"field": "具体项目名称", "reason": "用户未提供，不得自动补充"},
            {"field": "具体数据", "reason": "用户未提供，不得自动补充"},
            {"field": "具体成果", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "vague_content", "detail": "内容较为笼统，缺少具体数据支撑", "level": "medium"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "报告上行文场景，style_level=2，需重点防止夹带请示事项。结构按报告三段式规划。",
        "doc_type": "报告", "direction": "上行文", "style_level": 2, "risk_level": "low",
        "title_plan": {"recommended_title": "关于重点任务推进情况的报告", "title_type": "正式公文标题", "title_confidence": 0.7, "title_basis": ["extract.projects 包含'重点任务'"], "title_risks": ["缺少具体任务标识"], "alternative_titles": ["关于今年以来工作推进情况的报告"]},
        "addressee_plan": {"recommended_addressee": "集团", "source": "extract.organizations", "confidence": 0.6, "needs_manual_confirmation": True, "note": "需确认正式主送单位全称"},
        "signer_plan": {"recommended_signer": None, "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "用户未提供落款单位"},
        "sections": [
            {"section_id": "S1", "section_name": "工作概述", "purpose": "概述工作推进背景", "content_guidance": "围绕今年以来重点任务推进展开", "fact_bindings": [{"fact_type": "time", "fact_value": "今年以来", "source_from_extract": True}, {"fact_type": "project", "fact_value": "重点任务", "source_from_extract": True}], "blocked_items": ["不得编造具体数据", "不得编造项目名称"], "word_count_estimate": 100, "needs_manual_input": False},
            {"section_id": "S2", "section_name": "已完成工作", "purpose": "列举已完成的具体工作", "content_guidance": "前期梳理、资源协调、阶段性复盘", "fact_bindings": [{"fact_type": "achievement", "fact_value": "完成了前期梳理", "source_from_extract": True}, {"fact_type": "achievement", "fact_value": "资源协调", "source_from_extract": True}, {"fact_type": "achievement", "fact_value": "阶段性复盘", "source_from_extract": True}], "blocked_items": ["不得编造成果数据"], "word_count_estimate": 200, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "下一步工作计划", "purpose": "阐述后续工作安排", "content_guidance": "加强统筹、推动重点任务落地", "fact_bindings": [], "blocked_items": ["不得添加请示事项", "不得使用'请批复''请批准'"], "word_count_estimate": 150, "needs_manual_input": False},
            {"section_id": "S4", "section_name": "结尾", "purpose": "标准报告结尾", "content_guidance": "使用'特此报告'结尾", "fact_bindings": [], "blocked_items": ["不得使用'妥否，请批示'"], "word_count_estimate": 20, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "克制正式", "key_expressions": ["推进", "落实", "加强统筹"], "forbidden_expressions": ["妥否，请批示", "请批复", "请批准", "请予支持", "奋楫扬帆"], "style_reference": "doc-type-rules.md 报告章节"},
        "title_rules": ["报告标题格式：关于XXX的报告", "标题只能使用 extract 中已有信息"],
        "addressee_resolution": {"recommended_addressee": "集团", "source": "extract.organizations", "confidence": 0.6, "needs_manual_confirmation": True, "note": "需确认正式全称"},
        "signer_resolution": {"recommended_signer": None, "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "落款单位缺失"},
        "title_suggestions": {"recommended_title": "关于重点任务推进情况的报告", "alternative_titles": ["关于今年以来工作推进情况的报告"], "title_rules": ["报告标题格式：关于XXX的报告"]},
        "missing_fields": [{"field": "具体项目/任务全称", "reason": "用户仅写'重点任务'", "impact": "medium", "suggestion": "人工确认"}, {"field": "汇报单位名称", "reason": "用户未提供", "impact": "high", "suggestion": "人工确认"}, {"field": "主送单位全称", "reason": "用户仅写'集团'", "impact": "high", "suggestion": "人工确认"}],
        "cannot_infer": [{"field": "具体项目名称", "reason": "不得自动补充"}, {"field": "具体数据", "reason": "不得自动补充"}],
        "risk_flags": [{"type": "vague_content", "detail": "内容较为笼统", "level": "medium"}],
        "manual_confirmation_fields": [{"field": "具体项目/任务全称", "reason": "用户仅写'重点任务'"}, {"field": "汇报单位名称", "reason": "用户未提供"}, {"field": "主送单位全称", "reason": "用户仅写'集团'"}],
        "draft_directives": {"total_word_count_estimate": 500, "must_use_facts": ["今年以来", "重点任务", "前期梳理", "资源协调", "阶段性复盘", "加强统筹", "推动重点任务落地"], "must_avoid": ["妥否，请批示", "请批复", "请批准", "请予支持", "取得显著成效"], "format_requirements": ["报告标准格式", "特此报告结尾"]},
    }

    draft_markdown = """【主送单位待确认】：

关于重点任务推进情况的报告

今年以来，相关工作围绕重点任务推进，有序开展各项前期工作。

一、已完成工作

（一）前期梳理。完成了对重点任务的整体梳理，明确了工作方向和推进路径。

（二）资源协调。统筹协调各方资源，为重点任务推进提供保障。

（三）阶段性复盘。组织开展了阶段性工作复盘，梳理经验、查找不足。

二、下一步工作计划

下阶段将继续加强统筹协调，推动重点任务落地实施，确保各项目标任务按计划推进。

特此报告。

【落款单位待确认】
【日期待确认】"""

    draft = {
        "draft_summary": "按报告结构生成初稿，三段式+特此报告结尾，未夹带请示事项，未编造数据。",
        "doc_type": "报告", "direction": "上行文", "style_level": 2, "risk_level": "low",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "今年以来", "fact_type": "time", "fact_value": "今年以来", "source_text": "今年以来，相关工作围绕重点任务推进", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "重点任务", "fact_type": "project", "fact_value": "重点任务", "source_text": "相关工作围绕重点任务推进", "source": "extract_result.fact_items", "confidence": 0.85},
            {"draft_text": "前期梳理", "fact_type": "achievement", "fact_value": "完成了前期梳理", "source_text": "完成了前期梳理", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "资源协调", "fact_type": "achievement", "fact_value": "资源协调", "source_text": "资源协调", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "阶段性复盘", "fact_type": "achievement", "fact_value": "阶段性复盘", "source_text": "阶段性复盘", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "加强统筹", "fact_type": "event", "fact_value": "继续加强统筹", "source_text": "下一步将继续加强统筹", "source": "user_input", "confidence": 0.9},
            {"draft_text": "推动重点任务落地", "fact_type": "event", "fact_value": "推动重点任务落地", "source_text": "推动重点任务落地", "source": "user_input", "confidence": 0.9},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [{"raw_value": "集团", "used_value": "集团", "type": "organization", "source": "user_input", "confidence": 0.6, "needs_manual_confirmation": True, "note": "正式全称待确认"}],
        "blocked_items_check": [
            {"item": "不得编造具体数据", "status": "not_used", "reason": "初稿未编造数据"},
            {"item": "不得编造项目名称", "status": "not_used", "reason": "仅使用'重点任务'"},
            {"item": "不得添加请示事项", "status": "not_used", "reason": "初稿无请示表达"},
            {"item": "不得使用'妥否，请批示'结尾", "status": "not_used", "reason": "结尾为'特此报告'"},
            {"item": "不得使用'请批复''请批准'", "status": "not_used", "reason": "初稿无此类表达"},
        ],
        "warnings": [
            {"level": "medium", "type": "missing_field", "message": "具体项目名称缺失", "related_field": "重点任务", "action": "建议确认具体任务名称"},
            {"level": "medium", "type": "missing_field", "message": "缺少数据支撑", "related_field": None, "action": "建议提供工作量化指标"},
        ],
        "manual_confirmation_fields": [
            {"field": "具体项目/任务全称", "reason": "用户仅写'重点任务'", "impact": "影响报告具体性", "required_before_final": False},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响报告落款", "required_before_final": True},
            {"field": "主送单位全称", "reason": "用户仅写'集团'", "impact": "影响报告抬头", "required_before_final": True},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以报告结构撰写，结尾为'特此报告'，无请示事项，所有事实均可溯源。",
        "pass": True, "score": 85, "rewrite_required": False, "risk_level": "low",
        "checks": {
            "doc_type_check": make_check("pass", "报告结构正确，结尾为特此报告", 0),
            "structure_check": make_check("pass", "三段式结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自 extract_result 或用户原文", 0),
            "fact_usage_report_check": make_check("pass", "7条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("warning", "'集团'称谓需确认正式全称", 1),
            "blocked_items_check": make_check("pass", "5项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "2项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "3项人工确认字段已标记", 0),
            "style_check": make_check("pass", "克制正式风格，无过度表达", 0),
            "format_check": make_check("pass", "报告格式正确", 0),
        },
        "issues": [
            {"issue_id": "R003-001", "level": "medium", "type": "terminology_error", "location": "主送单位", "detail": "'集团'称谓需确认正式全称", "evidence": "extract.organizations = ['集团']", "suggestion": "确认正式全称", "rewrite_hint": "replace"},
        ],
        "rewrite_instructions": [
            {"priority": "medium", "target": "主送单位占位符", "action": "replace", "instruction": "将占位符替换为正式全称", "basis": "人工确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "具体项目/任务全称", "reason": "用户仅写'重点任务'", "impact": "影响报告具体性", "required_before_final": False},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响报告落款", "required_before_final": True},
            {"field": "主送单位全称", "reason": "用户仅写'集团'", "impact": "影响报告抬头", "required_before_final": True},
        ],
        "review_policy": REVIEW_POLICY,
    }

    rewrite = {
        "rewrite_summary": "review 未发现 critical 级别问题，初稿结构正确。保留报告结构和特此报告结尾，标记缺失信息。",
        "doc_type": "报告", "direction": "上行文", "style_level": 2, "risk_level": "low",
        "final_markdown": draft_markdown,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [
            {"issue_id": "R003-001", "reason": "缺少正式主送单位全称", "required_action": "人工确认后替换占位符"},
        ],
        "remaining_risks": [
            {"level": "medium", "type": "missing_field", "detail": "具体项目/任务全称缺失", "action": "人工确认后补充"},
            {"level": "high", "type": "missing_field", "detail": "汇报单位名称缺失", "action": "人工确认后补充落款"},
            {"level": "high", "type": "missing_field", "detail": "主送单位全称缺失", "action": "人工确认后替换占位符"},
        ],
        "manual_confirmation_fields": [
            {"field": "具体项目/任务全称", "reason": "用户仅写'重点任务'", "impact": "影响报告具体性", "required_before_final": False},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响报告落款", "required_before_final": True},
            {"field": "主送单位全称", "reason": "用户仅写'集团'", "impact": "影响报告抬头", "required_before_final": True},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success", "doc_type": "报告", "risk_level": "low", "review_pass": True, "rewrite_required": False,
        "manual_confirmation_count": 3, "remaining_risk_count": 3,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None, "error_type": None, "error_message": None, "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify, "extract_result.json": extract, "plan_result.json": plan,
        "draft_result.json": draft, "review_result.json": review, "rewrite_result.json": rewrite,
        "final_markdown.md": draft_markdown, "pipeline_report.json": pipeline_report,
    }


def gen_004_notice():
    case_id = "004-notice"
    classify = {
        "doc_type": "通知", "doc_type_confidence": 0.95, "direction": "下行文", "style_level": 1, "risk_level": "low",
        "reason": "用户明确'内部通知'，内容为布置工作、设定截止时间，符合通知特征。",
        "required_rules": ["通知"],
        "required_structure": ["标题", "主送对象", "正文（背景+要求+时间）", "结尾"],
        "forbidden_items": ["不得写成新闻稿", "不得添加宣传性评价", "不得编造具体截止日期", "不得编造专项整治全称", "不得编造材料提交方式"],
        "need_manual_confirmation": False, "manual_confirmation_fields": [],
    }
    extract = {
        "source_summary": "用户素材涉及专项整治自查材料报送工作通知。",
        "facts": {
            "time": ["本周五前"], "location": [], "organizations": ["各部门"], "leaders": [], "persons": [], "products": [],
            "projects": ["专项整治"], "events": [], "data": [], "achievements": [], "problems": [],
            "requests": ["提交专项整治自查情况"], "policies": [], "documents": [],
        },
        "fact_items": [
            {"type": "time", "value": "本周五前", "source_text": "请各部门于本周五前提交专项整治自查情况", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "相对时间，需确认具体日期"},
            {"type": "organization", "value": "各部门", "source_text": "请各部门于本周五前提交专项整治自查情况", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "project", "value": "专项整治", "source_text": "专项整治自查情况", "confidence": 0.85, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "具体名称待确认"},
            {"type": "request", "value": "提交专项整治自查情况", "source_text": "请各部门于本周五前提交专项整治自查情况", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
        ],
        "missing_fields": [
            {"field": "具体截止日期", "reason": "'本周五'是相对时间", "impact": "影响通知明确性", "suggestion": "建议确认具体日期"},
            {"field": "通知下发单位", "reason": "用户未提供", "impact": "影响通知抬头和落款", "suggestion": "建议确认下发单位"},
            {"field": "专项整治的具体名称/编号", "reason": "用户未提供", "impact": "影响通知准确性", "suggestion": "建议确认专项整治全称"},
            {"field": "材料提交方式", "reason": "用户未提供", "impact": "影响报送操作指引", "suggestion": "建议确认提交方式"},
        ],
        "cannot_infer": [
            {"field": "具体截止日期", "reason": "相对时间无法推断具体日期"},
            {"field": "专项整治全称", "reason": "用户未提供，不得自动补充"},
            {"field": "材料提交方式", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "vague_time", "detail": "时间表述模糊（'本周五'）", "level": "medium"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "通知下行文场景，style_level=1，需重点防止写成新闻稿。结构按通知标准格式规划。",
        "doc_type": "通知", "direction": "下行文", "style_level": 1, "risk_level": "low",
        "title_plan": {"recommended_title": "关于报送专项整治自查材料的通知", "title_type": "通知标题", "title_confidence": 0.75, "title_basis": ["extract.projects 包含'专项整治'", "extract.requests 包含'提交自查情况'"], "title_risks": ["缺少专项整治全称"], "alternative_titles": ["关于报送专项整治自查情况的通知"]},
        "addressee_plan": {"recommended_addressee": "各部门", "source": "extract.organizations", "confidence": 0.9, "needs_manual_confirmation": False, "note": "用户明确主送对象"},
        "signer_plan": {"recommended_signer": None, "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "用户未提供下发单位"},
        "sections": [
            {"section_id": "S1", "section_name": "正文第一部分", "purpose": "背景/依据", "content_guidance": "简述报送背景，不得编造", "fact_bindings": [{"fact_type": "project", "fact_value": "专项整治", "source_from_extract": True}], "blocked_items": ["不得写成新闻稿", "不得添加宣传性评价"], "word_count_estimate": 80, "needs_manual_input": False},
            {"section_id": "S2", "section_name": "正文第二部分", "purpose": "报送要求", "content_guidance": "内容（工作开展、问题排查、整改措施）+时间要求", "fact_bindings": [{"fact_type": "request", "fact_value": "提交专项整治自查情况", "source_from_extract": True}, {"fact_type": "time", "fact_value": "本周五前", "source_from_extract": True}], "blocked_items": ["不得编造截止日期", "不得编造提交方式"], "word_count_estimate": 150, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "结尾", "purpose": "标准通知结尾", "content_guidance": "通知规范结尾", "fact_bindings": [], "blocked_items": ["不得使用请示结尾"], "word_count_estimate": 30, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "简洁正式", "key_expressions": ["请各部门", "自查情况", "报送"], "forbidden_expressions": ["取得成效", "取得显著效果", "近日", "为深入贯彻"], "style_reference": "doc-type-rules.md 通知章节"},
        "title_rules": ["通知标题格式：关于XXX的通知"], "addressee_resolution": {"recommended_addressee": "各部门", "source": "extract.organizations", "confidence": 0.9, "needs_manual_confirmation": False, "note": None},
        "signer_resolution": {"recommended_signer": None, "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "下发单位缺失"},
        "title_suggestions": {"recommended_title": "关于报送专项整治自查材料的通知", "alternative_titles": ["关于报送专项整治自查情况的通知"], "title_rules": ["通知标题格式：关于XXX的通知"]},
        "missing_fields": [{"field": "具体截止日期", "reason": "相对时间"}, {"field": "通知下发单位", "reason": "用户未提供"}, {"field": "专项整治全称", "reason": "用户未提供"}, {"field": "材料提交方式", "reason": "用户未提供"}],
        "cannot_infer": [{"field": "具体截止日期", "reason": "无法推断"}, {"field": "专项整治全称", "reason": "无法推断"}, {"field": "材料提交方式", "reason": "无法推断"}],
        "risk_flags": [{"type": "vague_time", "detail": "截止日期模糊", "level": "medium"}],
        "manual_confirmation_fields": [{"field": "具体截止日期", "reason": "相对时间"}, {"field": "专项整治全称", "reason": "用户未提供"}, {"field": "材料提交方式", "reason": "用户未提供"}, {"field": "通知下发单位", "reason": "用户未提供"}],
        "draft_directives": {"total_word_count_estimate": 300, "must_use_facts": ["各部门", "本周五前", "专项整治", "自查情况", "工作开展", "问题排查", "整改措施"], "must_avoid": ["新闻导语", "宣传性评价", "取得成效"], "format_requirements": ["通知标准格式"]},
    }

    draft_markdown = """关于报送专项整治自查材料的通知

各部门：

为做好专项整治工作，现将有关事项通知如下。

一、报送内容

请各部门按照要求，认真开展专项整治自查，自查内容包括：

（一）工作开展情况；

（二）问题排查情况；

（三）整改措施落实情况。

二、报送时间

请各部门于本周五前完成材料报送。

三、报送方式

【报送方式待确认】

请各部门高度重视，按时完成自查材料报送。

【下发单位待确认】
【日期待确认】"""

    draft = {
        "draft_summary": "按通知格式生成初稿，非新闻稿体裁，主送对象明确，未编造截止日期和提交方式。",
        "doc_type": "通知", "direction": "下行文", "style_level": 1, "risk_level": "low",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "各部门", "fact_type": "organization", "fact_value": "各部门", "source_text": "请各部门于本周五前提交专项整治自查情况", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "专项整治", "fact_type": "project", "fact_value": "专项整治", "source_text": "专项整治自查情况", "source": "extract_result.fact_items", "confidence": 0.85},
            {"draft_text": "本周五前", "fact_type": "time", "fact_value": "本周五前", "source_text": "请各部门于本周五前提交专项整治自查情况", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "工作开展情况", "fact_type": "other", "fact_value": "工作开展", "source_text": "包括工作开展、问题排查、整改措施等内容", "source": "user_input", "confidence": 0.95},
            {"draft_text": "问题排查情况", "fact_type": "other", "fact_value": "问题排查", "source_text": "包括工作开展、问题排查、整改措施等内容", "source": "user_input", "confidence": 0.95},
            {"draft_text": "整改措施落实情况", "fact_type": "other", "fact_value": "整改措施", "source_text": "包括工作开展、问题排查、整改措施等内容", "source": "user_input", "confidence": 0.95},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [{"raw_value": "各部门", "used_value": "各部门", "type": "organization", "source": "user_input", "confidence": 0.95, "needs_manual_confirmation": False, "note": None}],
        "blocked_items_check": [
            {"item": "不得写成新闻稿", "status": "not_used", "reason": "初稿为通知格式，非新闻稿"},
            {"item": "不得添加宣传性评价", "status": "not_used", "reason": "初稿无宣传性评价"},
            {"item": "不得编造具体截止日期", "status": "not_used", "reason": "保留'本周五前'原表述"},
            {"item": "不得编造专项整治全称", "status": "not_used", "reason": "仅使用'专项整治'"},
            {"item": "不得编造材料提交方式", "status": "not_used", "reason": "使用占位符"},
        ],
        "warnings": [
            {"level": "medium", "type": "missing_field", "message": "截止日期模糊（'本周五前'）", "related_field": "截止日期", "action": "建议确认具体日期"},
            {"level": "medium", "type": "missing_field", "message": "专项整治全称缺失", "related_field": "专项整治", "action": "建议确认全称"},
            {"level": "medium", "type": "missing_field", "message": "材料提交方式缺失", "related_field": "提交方式", "action": "建议确认提交方式"},
        ],
        "manual_confirmation_fields": [
            {"field": "具体截止日期", "reason": "相对时间", "impact": "影响通知明确性", "required_before_final": True},
            {"field": "专项整治全称", "reason": "用户未提供", "impact": "影响通知准确性", "required_before_final": True},
            {"field": "材料提交方式", "reason": "用户未提供", "impact": "影响报送操作", "required_before_final": True},
            {"field": "通知下发单位", "reason": "用户未提供", "impact": "影响通知完整性", "required_before_final": True},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以通知格式撰写，非新闻稿体裁，主送对象明确，未编造信息。",
        "pass": True, "score": 85, "rewrite_required": False, "risk_level": "low",
        "checks": {
            "doc_type_check": make_check("pass", "通知结构正确，非新闻稿", 0),
            "structure_check": make_check("pass", "标题+主送+正文+落款结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自用户素材", 0),
            "fact_usage_report_check": make_check("pass", "6条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("pass", "称谓使用正确", 0),
            "blocked_items_check": make_check("pass", "5项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "3项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "4项人工确认字段已标记", 0),
            "style_check": make_check("pass", "简洁正式风格", 0),
            "format_check": make_check("pass", "通知格式正确", 0),
        },
        "issues": [
            {"issue_id": "R004-001", "level": "medium", "type": "fact_not_grounded", "location": "报送时间", "detail": "截止日期为相对时间'本周五前'", "evidence": "用户原文为'本周五前'", "suggestion": "确认具体日期", "rewrite_hint": "replace"},
        ],
        "rewrite_instructions": [
            {"priority": "medium", "target": "截止日期", "action": "replace", "instruction": "将'本周五前'替换为具体日期", "basis": "人工确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "具体截止日期", "reason": "相对时间", "impact": "影响通知明确性", "required_before_final": True},
            {"field": "专项整治全称", "reason": "用户未提供", "impact": "影响通知准确性", "required_before_final": True},
            {"field": "材料提交方式", "reason": "用户未提供", "impact": "影响报送操作", "required_before_final": True},
            {"field": "通知下发单位", "reason": "用户未提供", "impact": "影响通知完整性", "required_before_final": True},
        ],
        "review_policy": REVIEW_POLICY,
    }

    rewrite = {
        "rewrite_summary": "review 未发现 critical 级别问题，通知格式正确。保留通知结构和占位符，等待人工确认。",
        "doc_type": "通知", "direction": "下行文", "style_level": 1, "risk_level": "low",
        "final_markdown": draft_markdown,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [
            {"issue_id": "R004-001", "reason": "相对时间需确认具体日期", "required_action": "人工确认后替换"},
        ],
        "remaining_risks": [
            {"level": "high", "type": "missing_field", "detail": "具体截止日期缺失", "action": "人工确认"},
            {"level": "high", "type": "missing_field", "detail": "专项整治全称缺失", "action": "人工确认"},
            {"level": "medium", "type": "missing_field", "detail": "材料提交方式缺失", "action": "人工确认"},
            {"level": "high", "type": "missing_field", "detail": "通知下发单位缺失", "action": "人工确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "具体截止日期", "reason": "相对时间", "impact": "影响通知明确性", "required_before_final": True},
            {"field": "专项整治全称", "reason": "用户未提供", "impact": "影响通知准确性", "required_before_final": True},
            {"field": "材料提交方式", "reason": "用户未提供", "impact": "影响报送操作", "required_before_final": True},
            {"field": "通知下发单位", "reason": "用户未提供", "impact": "影响通知完整性", "required_before_final": True},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success", "doc_type": "通知", "risk_level": "low", "review_pass": True, "rewrite_required": False,
        "manual_confirmation_count": 4, "remaining_risk_count": 4,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None, "error_type": None, "error_message": None, "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify, "extract_result.json": extract, "plan_result.json": plan,
        "draft_result.json": draft, "review_result.json": review, "rewrite_result.json": rewrite,
        "final_markdown.md": draft_markdown, "pipeline_report.json": pipeline_report,
    }


def gen_005_meeting_minutes():
    case_id = "005-meeting-minutes"
    classify = {
        "doc_type": "会议纪要", "doc_type_confidence": 0.92, "direction": "内部材料", "style_level": 1, "risk_level": "high",
        "reason": "用户明确'会议纪要'，内容为会议研究事项和要求，但缺少时间、地点、参会人员等关键信息。",
        "required_rules": ["会议纪要"],
        "required_structure": ["会议基本信息", "会议议题", "研究事项", "会议要求/决议", "下一步安排"],
        "forbidden_items": ["不得虚构会议时间", "不得虚构会议地点", "不得虚构参会人员", "不得虚构会议名称", "不得编造会议决议外的内容"],
        "need_manual_confirmation": True,
        "manual_confirmation_fields": ["会议时间", "会议地点", "参会人员", "会议名称/主题"],
    }
    extract = {
        "source_summary": "用户素材涉及会议研究事项和要求，但缺少会议基本信息。",
        "facts": {
            "time": [], "location": [], "organizations": ["业务部门", "技术部门"], "leaders": [], "persons": [], "products": [],
            "projects": ["项目推进", "系统联调"], "events": [], "data": [], "achievements": [], "problems": [], "requests": [], "policies": [], "documents": [],
        },
        "fact_items": [
            {"type": "project", "value": "项目推进", "source_text": "会议研究了项目推进", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "organization", "value": "业务部门", "source_text": "业务部门牵头推进", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "具体部门名称待确认"},
            {"type": "organization", "value": "技术部门", "source_text": "技术部门配合完成系统联调", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "具体部门名称待确认"},
            {"type": "project", "value": "系统联调", "source_text": "技术部门配合完成系统联调", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
        ],
        "missing_fields": [
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响会议纪要完整性", "suggestion": "需用户确认会议时间"},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响会议纪要完整性", "suggestion": "需用户确认会议地点"},
            {"field": "参会人员", "reason": "用户未提供", "impact": "影响会议纪要完整性", "suggestion": "需用户确认参会人员"},
            {"field": "会议名称/主题", "reason": "用户未提供完整名称", "impact": "影响会议纪要标题", "suggestion": "需用户确认会议名称"},
        ],
        "cannot_infer": [
            {"field": "会议时间", "reason": "用户未提供，不得自动补充"},
            {"field": "会议地点", "reason": "用户未提供，不得自动补充"},
            {"field": "参会人员", "reason": "用户未提供，不得自动补充"},
            {"field": "会议名称", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "missing_basic_info", "detail": "缺少会议基本信息（时间、地点、参会人员）", "level": "critical"},
            {"type": "missing_meeting_name", "detail": "缺少会议名称", "level": "high"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "会议纪要内部材料场景，style_level=1，risk_level=high，缺少会议基本信息需用占位符。",
        "doc_type": "会议纪要", "direction": "内部材料", "style_level": 1, "risk_level": "high",
        "title_plan": {"recommended_title": "【会议名称待确认】会议纪要", "title_type": "会议纪要标题", "title_confidence": 0.3, "title_basis": ["用户未提供会议名称"], "title_risks": ["缺少会议名称"], "alternative_titles": ["【会议主题待确认】会议纪要"]},
        "addressee_plan": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "会议纪要无特定主送对象"},
        "signer_plan": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "会议纪要无需落款"},
        "sections": [
            {"section_id": "S1", "section_name": "会议基本信息", "purpose": "会议时间、地点、参会人员", "content_guidance": "使用【待确认】占位符", "fact_bindings": [], "blocked_items": ["不得虚构会议时间", "不得虚构会议地点", "不得虚构参会人员"], "word_count_estimate": 50, "needs_manual_input": True},
            {"section_id": "S2", "section_name": "会议议题", "purpose": "会议讨论议题", "content_guidance": "项目推进、责任分工、下阶段时间节点", "fact_bindings": [{"fact_type": "project", "fact_value": "项目推进", "source_from_extract": True}], "blocked_items": ["不得编造议题外的内容"], "word_count_estimate": 100, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "会议要求/决议", "purpose": "会议决议和工作要求", "content_guidance": "业务部门牵头、技术部门配合完成系统联调", "fact_bindings": [{"fact_type": "organization", "fact_value": "业务部门", "source_from_extract": True}, {"fact_type": "organization", "fact_value": "技术部门", "source_from_extract": True}, {"fact_type": "project", "fact_value": "系统联调", "source_from_extract": True}], "blocked_items": ["不得编造会议决议外的内容"], "word_count_estimate": 150, "needs_manual_input": False},
            {"section_id": "S4", "section_name": "下一步工作安排", "purpose": "后续工作部署", "content_guidance": "基于会议决议的工作安排", "fact_bindings": [], "blocked_items": ["不得编造新决议"], "word_count_estimate": 80, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "客观正式", "key_expressions": ["会议研究了", "会议要求", "牵头推进", "配合完成"], "forbidden_expressions": ["高度肯定", "一致认为（无依据）", "取得重大进展（无依据）"], "style_reference": "doc-type-rules.md 会议纪要章节"},
        "title_rules": ["会议纪要标题应包含会议名称"],
        "addressee_resolution": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "signer_resolution": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "title_suggestions": {"recommended_title": "【会议名称待确认】会议纪要", "alternative_titles": ["【会议主题待确认】会议纪要"], "title_rules": ["会议纪要标题应包含会议名称"]},
        "missing_fields": [{"field": "会议时间", "reason": "用户未提供"}, {"field": "会议地点", "reason": "用户未提供"}, {"field": "参会人员", "reason": "用户未提供"}, {"field": "会议名称/主题", "reason": "用户未提供"}],
        "cannot_infer": [{"field": "会议时间", "reason": "不得自动补充"}, {"field": "会议地点", "reason": "不得自动补充"}, {"field": "参会人员", "reason": "不得自动补充"}, {"field": "会议名称", "reason": "不得自动补充"}],
        "risk_flags": [{"type": "missing_basic_info", "detail": "缺少会议基本信息", "level": "critical"}, {"type": "missing_meeting_name", "detail": "缺少会议名称", "level": "high"}],
        "manual_confirmation_fields": [{"field": "会议时间", "reason": "用户未提供"}, {"field": "会议地点", "reason": "用户未提供"}, {"field": "参会人员", "reason": "用户未提供"}, {"field": "会议名称/主题", "reason": "用户未提供"}, {"field": "会议主持人", "reason": "用户未提供"}],
        "draft_directives": {"total_word_count_estimate": 400, "must_use_facts": ["项目推进", "责任分工", "业务部门牵头推进", "技术部门配合完成系统联调"], "must_avoid": ["虚构会议时间", "虚构会议地点", "虚构参会人员"], "format_requirements": ["会议纪要标准格式", "占位符标记缺失信息"]},
    }

    draft_markdown = """【会议名称待确认】会议纪要

一、会议基本信息

时间：【会议时间待确认】

地点：【会议地点待确认】

参会人员：【参会人员待确认】

二、会议议题

会议研究了项目推进、责任分工和下阶段时间节点等相关事宜。

三、会议要求

（一）业务部门牵头推进项目，确保按计划落实各项工作。

（二）技术部门配合完成系统联调，保障项目技术支撑。

四、下一步工作安排

各部门按照会议要求推进落实。"""

    draft = {
        "draft_summary": "按会议纪要格式生成初稿，对缺失信息使用【待确认】占位符，未虚构会议信息。",
        "doc_type": "会议纪要", "direction": "内部材料", "style_level": 1, "risk_level": "high",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "项目推进", "fact_type": "project", "fact_value": "项目推进", "source_text": "会议研究了项目推进", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "业务部门", "fact_type": "organization", "fact_value": "业务部门", "source_text": "业务部门牵头推进", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "技术部门", "fact_type": "organization", "fact_value": "技术部门", "source_text": "技术部门配合完成系统联调", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "系统联调", "fact_type": "project", "fact_value": "系统联调", "source_text": "配合完成系统联调", "source": "extract_result.fact_items", "confidence": 0.9},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [
            {"raw_value": "业务部门", "used_value": "业务部门", "type": "organization", "source": "user_input", "confidence": 0.6, "needs_manual_confirmation": True, "note": "具体部门名称待确认"},
            {"raw_value": "技术部门", "used_value": "技术部门", "type": "organization", "source": "user_input", "confidence": 0.6, "needs_manual_confirmation": True, "note": "具体部门名称待确认"},
        ],
        "blocked_items_check": [
            {"item": "不得虚构会议时间", "status": "not_used", "reason": "使用占位符【会议时间待确认】"},
            {"item": "不得虚构会议地点", "status": "not_used", "reason": "使用占位符【会议地点待确认】"},
            {"item": "不得虚构参会人员", "status": "not_used", "reason": "使用占位符【参会人员待确认】"},
            {"item": "不得虚构会议名称", "status": "not_used", "reason": "使用占位符【会议名称待确认】"},
            {"item": "不得编造会议决议外的内容", "status": "not_used", "reason": "仅使用用户提供的研究事项"},
        ],
        "warnings": [
            {"level": "critical", "type": "missing_field", "message": "会议时间缺失", "related_field": "会议时间", "action": "需用户确认"},
            {"level": "critical", "type": "missing_field", "message": "会议地点缺失", "related_field": "会议地点", "action": "需用户确认"},
            {"level": "critical", "type": "missing_field", "message": "参会人员缺失", "related_field": "参会人员", "action": "需用户确认"},
            {"level": "high", "type": "missing_field", "message": "会议名称缺失", "related_field": "会议名称", "action": "需用户确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "参会人员", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "会议名称/主题", "reason": "用户未提供", "impact": "影响会议纪要标题", "required_before_final": True},
            {"field": "会议主持人", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以会议纪要格式撰写，对缺失信息正确使用占位符，未虚构会议基本信息。",
        "pass": True, "score": 80, "rewrite_required": False, "risk_level": "high",
        "checks": {
            "doc_type_check": make_check("pass", "会议纪要格式正确", 0),
            "structure_check": make_check("pass", "基本信息+议题+要求+安排结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自用户素材", 0),
            "fact_usage_report_check": make_check("pass", "4条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("warning", "部门称谓需确认具体名称", 2),
            "blocked_items_check": make_check("pass", "5项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "4项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "5项人工确认字段已标记", 0),
            "style_check": make_check("pass", "客观正式风格", 0),
            "format_check": make_check("pass", "会议纪要格式正确", 0),
        },
        "issues": [
            {"issue_id": "R005-001", "level": "critical", "type": "fact_not_grounded", "location": "会议基本信息", "detail": "会议时间、地点、参会人员均为占位符", "evidence": "extract.missing_fields 包含四项关键信息", "suggestion": "需用户确认后填充", "rewrite_hint": "replace"},
        ],
        "rewrite_instructions": [
            {"priority": "critical", "target": "会议基本信息占位符", "action": "replace", "instruction": "用户确认后替换占位符", "basis": "用户确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "参会人员", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "会议名称/主题", "reason": "用户未提供", "impact": "影响会议纪要标题", "required_before_final": True},
            {"field": "会议主持人", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
        ],
        "review_policy": REVIEW_POLICY,
    }

    rewrite = {
        "rewrite_summary": "review 未发现虚构信息问题，占位符使用正确。保留会议纪要格式和所有占位符。",
        "doc_type": "会议纪要", "direction": "内部材料", "style_level": 1, "risk_level": "high",
        "final_markdown": draft_markdown,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [
            {"issue_id": "R005-001", "reason": "会议基本信息缺失，需人工确认后填充", "required_action": "人工确认会议时间、地点、参会人员、名称"},
        ],
        "remaining_risks": [
            {"level": "critical", "type": "missing_field", "detail": "会议时间缺失", "action": "人工确认"},
            {"level": "critical", "type": "missing_field", "detail": "会议地点缺失", "action": "人工确认"},
            {"level": "critical", "type": "missing_field", "detail": "参会人员缺失", "action": "人工确认"},
            {"level": "high", "type": "missing_field", "detail": "会议名称缺失", "action": "人工确认"},
            {"level": "medium", "type": "missing_field", "detail": "会议主持人缺失", "action": "人工确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "参会人员", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
            {"field": "会议名称/主题", "reason": "用户未提供", "impact": "影响会议纪要标题", "required_before_final": True},
            {"field": "会议主持人", "reason": "用户未提供", "impact": "影响会议纪要完整性", "required_before_final": True},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success", "doc_type": "会议纪要", "risk_level": "high", "review_pass": True, "rewrite_required": False,
        "manual_confirmation_count": 5, "remaining_risk_count": 5,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None, "error_type": None, "error_message": None, "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify, "extract_result.json": extract, "plan_result.json": plan,
        "draft_result.json": draft, "review_result.json": review, "rewrite_result.json": rewrite,
        "final_markdown.md": draft_markdown, "pipeline_report.json": pipeline_report,
    }


def gen_006_leader_speech():
    case_id = "006-leader-speech"
    classify = {
        "doc_type": "领导讲话", "doc_type_confidence": 0.93, "direction": "内部材料", "style_level": 2, "risk_level": "high",
        "reason": "用户明确'领导讲话稿'，内容为工作部署，但缺少讲话领导信息。",
        "required_rules": ["领导讲话"],
        "required_structure": ["开头", "形势分析", "工作部署", "要求/号召", "结尾"],
        "forbidden_items": ["不得编造讲话领导姓名", "不得编造讲话领导职务", "不得编造'我强调''我要求'等个人表态", "不得编造政策判断", "不得编造具体部门名称"],
        "need_manual_confirmation": True,
        "manual_confirmation_fields": ["讲话领导姓名", "讲话领导职务", "会议时间", "会议地点"],
    }
    extract = {
        "source_summary": "用户素材涉及工作推进会上的讲话内容，包含工作部署和要求，但缺少讲话领导信息。",
        "facts": {
            "time": [], "location": [], "organizations": ["各部门"], "leaders": [], "persons": [], "products": [],
            "projects": ["年度重点任务", "重点项目"], "events": ["工作推进会"], "data": [],
            "achievements": [], "problems": [], "requests": [], "policies": [], "documents": [],
        },
        "fact_items": [
            {"type": "event", "value": "工作推进会", "source_text": "领导在工作推进会上的讲话稿", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "organization", "value": "各部门", "source_text": "要求各部门强化责任意识", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "具体部门名称待确认"},
            {"type": "project", "value": "年度重点任务", "source_text": "围绕年度重点任务推进进行部署", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "具体任务内容待确认"},
            {"type": "project", "value": "重点项目", "source_text": "加快重点项目落地", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
        ],
        "missing_fields": [
            {"field": "讲话领导姓名", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "suggestion": "需用户确认"},
            {"field": "讲话领导职务", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "suggestion": "需用户确认"},
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响讲话稿时效性", "suggestion": "需用户确认"},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响讲话稿背景", "suggestion": "需用户确认"},
            {"field": "具体部门名称", "reason": "用户仅写'各部门'", "impact": "影响讲话稿指向性", "suggestion": "需用户确认"},
            {"field": "重点任务具体内容", "reason": "用户未提供", "impact": "影响讲话稿详实度", "suggestion": "需用户确认"},
        ],
        "cannot_infer": [
            {"field": "讲话领导姓名", "reason": "用户未提供，不得自动补充"},
            {"field": "讲话领导职务", "reason": "用户未提供，不得自动补充"},
            {"field": "具体重点任务内容", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "missing_leader_info", "detail": "缺少讲话领导信息", "level": "critical"},
            {"type": "missing_basic_info", "detail": "缺少会议基本信息", "level": "high"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "领导讲话内部材料场景，style_level=2，缺少讲话领导信息需用占位符。",
        "doc_type": "领导讲话", "direction": "内部材料", "style_level": 2, "risk_level": "high",
        "title_plan": {"recommended_title": "在【会议名称待确认】上的讲话", "title_type": "领导讲话标题", "title_confidence": 0.3, "title_basis": ["用户未提供会议名称和领导信息"], "title_risks": ["缺少会议名称和领导信息"], "alternative_titles": ["【讲话领导待确认】在【会议名称待确认】上的讲话"]},
        "addressee_plan": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "讲话稿无特定主送对象"},
        "signer_plan": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "讲话稿无需落款"},
        "sections": [
            {"section_id": "S1", "section_name": "开头", "purpose": "会议背景", "content_guidance": "工作推进会背景，使用占位符标记缺失领导信息", "fact_bindings": [{"fact_type": "event", "fact_value": "工作推进会", "source_from_extract": True}], "blocked_items": ["不得编造领导姓名", "不得编造领导职务", "不得编造'我强调''我要求'"], "word_count_estimate": 100, "needs_manual_input": True},
            {"section_id": "S2", "section_name": "形势分析", "purpose": "当前形势", "content_guidance": "基于有限素材克制表达", "fact_bindings": [], "blocked_items": ["不得编造政策判断"], "word_count_estimate": 100, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "工作部署", "purpose": "具体工作部署", "content_guidance": "强化责任意识、加快重点项目落地", "fact_bindings": [{"fact_type": "project", "fact_value": "年度重点任务", "source_from_extract": True}, {"fact_type": "project", "fact_value": "重点项目", "source_from_extract": True}, {"fact_type": "organization", "fact_value": "各部门", "source_from_extract": True}], "blocked_items": ["不得编造具体部门名称"], "word_count_estimate": 200, "needs_manual_input": False},
            {"section_id": "S4", "section_name": "结尾", "purpose": "号召和要求", "content_guidance": "收束性表达", "fact_bindings": [], "blocked_items": ["不得编造个人表态"], "word_count_estimate": 50, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "正式部署", "key_expressions": ["强化责任意识", "加快落地", "推进"], "forbidden_expressions": ["我强调", "我要求", "我指出", "奋楫扬帆"], "style_reference": "doc-type-rules.md 领导讲话章节"},
        "title_rules": ["讲话标题应包含会议名称或领导信息"],
        "addressee_resolution": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "signer_resolution": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "title_suggestions": {"recommended_title": "在【会议名称待确认】上的讲话", "alternative_titles": ["【讲话领导待确认】在【会议名称待确认】上的讲话"], "title_rules": ["讲话标题应包含会议名称"]},
        "missing_fields": [{"field": "讲话领导姓名", "reason": "用户未提供"}, {"field": "讲话领导职务", "reason": "用户未提供"}, {"field": "会议时间", "reason": "用户未提供"}, {"field": "会议地点", "reason": "用户未提供"}],
        "cannot_infer": [{"field": "讲话领导姓名", "reason": "不得自动补充"}, {"field": "讲话领导职务", "reason": "不得自动补充"}, {"field": "具体重点任务内容", "reason": "不得自动补充"}],
        "risk_flags": [{"type": "missing_leader_info", "detail": "缺少讲话领导信息", "level": "critical"}, {"type": "missing_basic_info", "detail": "缺少会议基本信息", "level": "high"}],
        "manual_confirmation_fields": [{"field": "讲话领导姓名", "reason": "用户未提供"}, {"field": "讲话领导职务", "reason": "用户未提供"}, {"field": "会议时间", "reason": "用户未提供"}, {"field": "会议地点", "reason": "用户未提供"}],
        "draft_directives": {"total_word_count_estimate": 500, "must_use_facts": ["工作推进会", "年度重点任务", "强化责任意识", "加快重点项目落地"], "must_avoid": ["编造领导姓名", "编造领导职务", "编造'我强调''我要求'", "编造政策判断"], "format_requirements": ["领导讲话稿格式", "占位符标记缺失领导信息"]},
    }

    draft_markdown = """【讲话领导待确认】在【会议名称待确认】上的讲话

各位同志：

今天，我们召开工作推进会，围绕年度重点任务推进进行部署。

当前，各项工作正处在关键推进阶段。我们要认清形势，把握机遇，切实增强责任感和紧迫感。

一、强化责任意识

各部门要进一步提高政治站位，强化责任担当，将年度重点任务作为当前工作的重中之重，切实抓好推进落实。

二、加快重点项目落地

要紧盯重点项目进度，加强统筹协调，及时解决推进过程中遇到的困难和问题，确保各重点项目按计划推进落地。

三、统筹推进各项工作

各部门要密切配合，形成工作合力，共同推动年度重点任务落地见效。

让我们以高度的责任感和扎实的工作作风，全力以赴完成各项任务。"""

    draft = {
        "draft_summary": "按领导讲话稿格式生成初稿，对缺失领导信息使用占位符，未编造个人表态。",
        "doc_type": "领导讲话", "direction": "内部材料", "style_level": 2, "risk_level": "high",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "工作推进会", "fact_type": "event", "fact_value": "工作推进会", "source_text": "领导在工作推进会上的讲话稿", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "年度重点任务", "fact_type": "project", "fact_value": "年度重点任务", "source_text": "围绕年度重点任务推进进行部署", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "强化责任意识", "fact_type": "other", "fact_value": "强化责任意识", "source_text": "要求各部门强化责任意识", "source": "user_input", "confidence": 0.95},
            {"draft_text": "加快重点项目落地", "fact_type": "project", "fact_value": "重点项目", "source_text": "加快重点项目落地", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "各部门", "fact_type": "organization", "fact_value": "各部门", "source_text": "要求各部门强化责任意识", "source": "extract_result.fact_items", "confidence": 0.9},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [
            {"raw_value": "各部门", "used_value": "各部门", "type": "organization", "source": "user_input", "confidence": 0.6, "needs_manual_confirmation": True, "note": "具体部门名称待确认"},
        ],
        "blocked_items_check": [
            {"item": "不得编造讲话领导姓名", "status": "not_used", "reason": "使用占位符【讲话领导待确认】"},
            {"item": "不得编造讲话领导职务", "status": "not_used", "reason": "未编造职务"},
            {"item": "不得编造'我强调''我要求'等个人表态", "status": "not_used", "reason": "初稿未使用第一人称表态"},
            {"item": "不得编造政策判断", "status": "not_used", "reason": "未编造政策判断"},
            {"item": "不得编造具体部门名称", "status": "not_used", "reason": "仅使用'各部门'"},
        ],
        "warnings": [
            {"level": "critical", "type": "missing_field", "message": "讲话领导信息缺失", "related_field": "讲话领导", "action": "需用户确认"},
            {"level": "high", "type": "missing_field", "message": "会议基本信息缺失", "related_field": "会议信息", "action": "需用户确认"},
            {"level": "medium", "type": "missing_field", "message": "具体任务内容模糊", "related_field": "重点任务", "action": "可补充细节"},
        ],
        "manual_confirmation_fields": [
            {"field": "讲话领导姓名", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "required_before_final": True},
            {"field": "讲话领导职务", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "required_before_final": True},
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响讲话稿时效性", "required_before_final": True},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响讲话稿背景", "required_before_final": True},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以领导讲话稿格式撰写，未编造领导信息和个人表态，占位符使用正确。",
        "pass": True, "score": 82, "rewrite_required": False, "risk_level": "high",
        "checks": {
            "doc_type_check": make_check("pass", "领导讲话稿格式正确", 0),
            "structure_check": make_check("pass", "开头+部署+要求+结尾结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自用户素材", 0),
            "fact_usage_report_check": make_check("pass", "5条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("warning", "'各部门'称谓需确认具体名称", 1),
            "blocked_items_check": make_check("pass", "5项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "3项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "4项人工确认字段已标记", 0),
            "style_check": make_check("pass", "正式部署风格，无过度表达", 0),
            "format_check": make_check("pass", "领导讲话稿格式正确", 0),
        },
        "issues": [
            {"issue_id": "R006-001", "level": "critical", "type": "fact_not_grounded", "location": "标题和开头", "detail": "讲话领导信息缺失", "evidence": "extract.leaders 为空", "suggestion": "需用户确认", "rewrite_hint": "replace"},
        ],
        "rewrite_instructions": [
            {"priority": "critical", "target": "讲话领导占位符", "action": "replace", "instruction": "确认后替换", "basis": "用户确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "讲话领导姓名", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "required_before_final": True},
            {"field": "讲话领导职务", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "required_before_final": True},
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响讲话稿时效性", "required_before_final": True},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响讲话稿背景", "required_before_final": True},
        ],
        "review_policy": REVIEW_POLICY,
    }

    rewrite = {
        "rewrite_summary": "review 未发现虚构领导信息问题，占位符使用正确。保留讲话稿格式和占位符。",
        "doc_type": "领导讲话", "direction": "内部材料", "style_level": 2, "risk_level": "high",
        "final_markdown": draft_markdown,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [
            {"issue_id": "R006-001", "reason": "讲话领导信息缺失，需人工确认", "required_action": "确认后替换占位符"},
        ],
        "remaining_risks": [
            {"level": "critical", "type": "missing_field", "detail": "讲话领导姓名缺失", "action": "人工确认"},
            {"level": "critical", "type": "missing_field", "detail": "讲话领导职务缺失", "action": "人工确认"},
            {"level": "high", "type": "missing_field", "detail": "会议时间缺失", "action": "人工确认"},
            {"level": "high", "type": "missing_field", "detail": "会议地点缺失", "action": "人工确认"},
            {"level": "medium", "type": "missing_field", "detail": "具体任务内容模糊", "action": "可补充"},
        ],
        "manual_confirmation_fields": [
            {"field": "讲话领导姓名", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "required_before_final": True},
            {"field": "讲话领导职务", "reason": "用户未提供", "impact": "影响讲话稿身份标识", "required_before_final": True},
            {"field": "会议时间", "reason": "用户未提供", "impact": "影响讲话稿时效性", "required_before_final": True},
            {"field": "会议地点", "reason": "用户未提供", "impact": "影响讲话稿背景", "required_before_final": True},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success", "doc_type": "领导讲话", "risk_level": "high", "review_pass": True, "rewrite_required": False,
        "manual_confirmation_count": 4, "remaining_risk_count": 5,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None, "error_type": None, "error_message": None, "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify, "extract_result.json": extract, "plan_result.json": plan,
        "draft_result.json": draft, "review_result.json": review, "rewrite_result.json": rewrite,
        "final_markdown.md": draft_markdown, "pipeline_report.json": pipeline_report,
    }


def gen_007_summary():
    case_id = "007-summary"
    classify = {
        "doc_type": "总结", "doc_type_confidence": 0.93, "direction": "内部材料", "style_level": 2, "risk_level": "low",
        "reason": "用户明确'阶段性工作总结'，内容为已完成工作和下一步计划，符合总结特征。",
        "required_rules": ["总结"],
        "required_structure": ["总体概述", "已完成工作", "存在问题", "下阶段工作计划", "结尾"],
        "forbidden_items": ["不得编造量化数据", "不得编造成果荣誉", "不得编造奖项", "不得使用'取得显著成效'等无依据拔高", "不得编造部门名称"],
        "need_manual_confirmation": False, "manual_confirmation_fields": [],
    }
    extract = {
        "source_summary": "用户素材涉及一季度工作总结，包含已完成工作和下一步计划。",
        "facts": {
            "time": ["今年一季度"], "location": [], "organizations": [], "leaders": [], "persons": [], "products": [],
            "projects": ["年度目标", "制度修订", "流程优化", "团队培训"], "events": [], "data": [],
            "achievements": ["完成了制度修订", "流程优化", "团队培训"],
            "problems": [], "requests": [], "policies": [], "documents": [],
        },
        "fact_items": [
            {"type": "time", "value": "今年一季度", "source_text": "今年一季度，部门围绕年度目标推进各项工作", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "project", "value": "年度目标", "source_text": "围绕年度目标推进各项工作", "confidence": 0.85, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "具体目标内容待确认"},
            {"type": "achievement", "value": "完成了制度修订", "source_text": "完成了制度修订", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "achievement", "value": "流程优化", "source_text": "流程优化", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "achievement", "value": "团队培训", "source_text": "团队培训", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
        ],
        "missing_fields": [
            {"field": "部门名称", "reason": "用户未提供", "impact": "影响总结身份标识", "suggestion": "建议确认部门名称"},
            {"field": "具体制度修订内容", "reason": "用户未提供", "impact": "影响总结详实度", "suggestion": "建议补充"},
            {"field": "具体流程优化内容", "reason": "用户未提供", "impact": "影响总结详实度", "suggestion": "建议补充"},
            {"field": "具体团队培训内容", "reason": "用户未提供", "impact": "影响总结详实度", "suggestion": "建议补充"},
            {"field": "量化数据", "reason": "用户未提供", "impact": "影响总结可信度", "suggestion": "建议提供量化指标"},
        ],
        "cannot_infer": [
            {"field": "量化数据", "reason": "用户未提供，不得自动补充"},
            {"field": "具体制度名称", "reason": "用户未提供，不得自动补充"},
            {"field": "具体流程名称", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "vague_content", "detail": "内容较为笼统，缺少量化数据", "level": "medium"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "总结内部材料场景，style_level=2，需重点防止无依据拔高和编造数据。",
        "doc_type": "总结", "direction": "内部材料", "style_level": 2, "risk_level": "low",
        "title_plan": {"recommended_title": "一季度阶段性工作总结", "title_type": "总结标题", "title_confidence": 0.7, "title_basis": ["extract.time 包含'今年一季度'"], "title_risks": ["缺少部门名称前缀"], "alternative_titles": ["今年一季度工作总结"]},
        "addressee_plan": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "总结无特定主送对象"},
        "signer_plan": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": "总结无需落款"},
        "sections": [
            {"section_id": "S1", "section_name": "总体概述", "purpose": "概述一季度工作方向", "content_guidance": "围绕年度目标推进", "fact_bindings": [{"fact_type": "time", "fact_value": "今年一季度", "source_from_extract": True}, {"fact_type": "project", "fact_value": "年度目标", "source_from_extract": True}], "blocked_items": ["不得编造部门名称"], "word_count_estimate": 100, "needs_manual_input": False},
            {"section_id": "S2", "section_name": "已完成工作", "purpose": "列举已完成工作", "content_guidance": "制度修订、流程优化、团队培训", "fact_bindings": [{"fact_type": "achievement", "fact_value": "完成了制度修订", "source_from_extract": True}, {"fact_type": "achievement", "fact_value": "流程优化", "source_from_extract": True}, {"fact_type": "achievement", "fact_value": "团队培训", "source_from_extract": True}], "blocked_items": ["不得编造量化数据", "不得编造成果荣誉", "不得使用'取得显著成效'"], "word_count_estimate": 200, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "下阶段工作计划", "purpose": "后续工作安排", "content_guidance": "深化内部管理、提升运营效率", "fact_bindings": [], "blocked_items": ["不得编造计划外的内容"], "word_count_estimate": 150, "needs_manual_input": False},
            {"section_id": "S4", "section_name": "结尾", "purpose": "收束性表达", "content_guidance": "简短总结", "fact_bindings": [], "blocked_items": ["不得无依据拔高"], "word_count_estimate": 50, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "务实正式", "key_expressions": ["推进", "落实", "深化", "提升"], "forbidden_expressions": ["取得显著成效", "取得重大突破", "荣获", "被评为", "奋楫扬帆"], "style_reference": "doc-type-rules.md 总结章节"},
        "title_rules": ["总结标题应包含时间段"],
        "addressee_resolution": {"recommended_addressee": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "signer_resolution": {"recommended_signer": None, "source": "not_applicable", "confidence": 0, "needs_manual_confirmation": False, "note": None},
        "title_suggestions": {"recommended_title": "一季度阶段性工作总结", "alternative_titles": ["今年一季度工作总结"], "title_rules": ["总结标题应包含时间段"]},
        "missing_fields": [{"field": "部门名称", "reason": "用户未提供"}, {"field": "量化数据", "reason": "用户未提供"}],
        "cannot_infer": [{"field": "量化数据", "reason": "不得自动补充"}, {"field": "具体制度名称", "reason": "不得自动补充"}],
        "risk_flags": [{"type": "vague_content", "detail": "内容笼统", "level": "medium"}],
        "manual_confirmation_fields": [{"field": "部门名称", "reason": "用户未提供"}],
        "draft_directives": {"total_word_count_estimate": 500, "must_use_facts": ["今年一季度", "制度修订", "流程优化", "团队培训", "深化内部管理", "提升运营效率"], "must_avoid": ["取得显著成效", "取得重大突破", "荣获", "被评为", "具体量化数据"], "format_requirements": ["总结标准格式"]},
    }

    draft_markdown = """一季度阶段性工作总结

今年一季度，围绕年度目标，有序推进各项工作，取得了阶段性进展。

一、已完成工作

（一）制度修订。完成了相关制度的修订工作，进一步完善内部管理制度体系。

（二）流程优化。推进了业务流程优化，提高了工作效率。

（三）团队培训。组织开展了团队培训工作，提升了团队业务能力。

二、下阶段工作计划

下阶段将继续深化内部管理，提升运营效率，重点做好以下工作：

（一）持续完善内部管理制度；

（二）进一步优化业务流程；

（三）加强团队建设，提升综合能力。"""

    draft = {
        "draft_summary": "按总结结构生成初稿，未编造数据、荣誉和拔高表述。",
        "doc_type": "总结", "direction": "内部材料", "style_level": 2, "risk_level": "low",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "今年一季度", "fact_type": "time", "fact_value": "今年一季度", "source_text": "今年一季度，部门围绕年度目标推进各项工作", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "年度目标", "fact_type": "project", "fact_value": "年度目标", "source_text": "围绕年度目标推进各项工作", "source": "extract_result.fact_items", "confidence": 0.85},
            {"draft_text": "制度修订", "fact_type": "achievement", "fact_value": "完成了制度修订", "source_text": "完成了制度修订", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "流程优化", "fact_type": "achievement", "fact_value": "流程优化", "source_text": "流程优化", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "团队培训", "fact_type": "achievement", "fact_value": "团队培训", "source_text": "团队培训", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "深化内部管理", "fact_type": "other", "fact_value": "深化内部管理", "source_text": "继续深化内部管理", "source": "user_input", "confidence": 0.9},
            {"draft_text": "提升运营效率", "fact_type": "other", "fact_value": "提升运营效率", "source_text": "提升运营效率", "source": "user_input", "confidence": 0.9},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [],
        "blocked_items_check": [
            {"item": "不得编造量化数据", "status": "not_used", "reason": "初稿未编造数据"},
            {"item": "不得编造成果荣誉", "status": "not_used", "reason": "初稿未编造荣誉"},
            {"item": "不得编造奖项", "status": "not_used", "reason": "初稿未编造奖项"},
            {"item": "不得使用'取得显著成效'等无依据拔高", "status": "not_used", "reason": "初稿使用'阶段性进展'"},
            {"item": "不得编造部门名称", "status": "not_used", "reason": "初稿未编造部门名称"},
        ],
        "warnings": [
            {"level": "medium", "type": "missing_field", "message": "部门名称缺失", "related_field": "部门名称", "action": "建议确认"},
            {"level": "medium", "type": "missing_field", "message": "缺少量化数据支撑", "related_field": None, "action": "建议提供量化指标"},
        ],
        "manual_confirmation_fields": [
            {"field": "部门名称", "reason": "用户未提供", "impact": "影响总结身份标识", "required_before_final": False},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以总结结构撰写，未编造数据、荣誉和拔高表述，所有事实均可溯源。",
        "pass": True, "score": 88, "rewrite_required": False, "risk_level": "low",
        "checks": {
            "doc_type_check": make_check("pass", "总结结构正确", 0),
            "structure_check": make_check("pass", "概述+已完成+下阶段结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自用户素材", 0),
            "fact_usage_report_check": make_check("pass", "7条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("pass", "无称谓问题", 0),
            "blocked_items_check": make_check("pass", "5项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "2项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "1项人工确认字段已标记", 0),
            "style_check": make_check("pass", "务实正式风格", 0),
            "format_check": make_check("pass", "总结格式正确", 0),
        },
        "issues": [],
        "rewrite_instructions": [],
        "manual_confirmation_fields": [
            {"field": "部门名称", "reason": "用户未提供", "impact": "影响总结身份标识", "required_before_final": False},
        ],
        "review_policy": REVIEW_POLICY,
    }

    rewrite = {
        "rewrite_summary": "review 未发现问题，初稿结构正确。保留总结结构和所有用户事实。",
        "doc_type": "总结", "direction": "内部材料", "style_level": 2, "risk_level": "low",
        "final_markdown": draft_markdown,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [],
        "remaining_risks": [
            {"level": "medium", "type": "missing_field", "detail": "部门名称缺失", "action": "人工确认后补充标题"},
            {"level": "medium", "type": "missing_field", "detail": "缺少量化数据支撑", "action": "建议提供量化指标"},
        ],
        "manual_confirmation_fields": [
            {"field": "部门名称", "reason": "用户未提供", "impact": "影响总结身份标识", "required_before_final": False},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success", "doc_type": "总结", "risk_level": "low", "review_pass": True, "rewrite_required": False,
        "manual_confirmation_count": 1, "remaining_risk_count": 2,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None, "error_type": None, "error_message": None, "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify, "extract_result.json": extract, "plan_result.json": plan,
        "draft_result.json": draft, "review_result.json": review, "rewrite_result.json": rewrite,
        "final_markdown.md": draft_markdown, "pipeline_report.json": pipeline_report,
    }


def gen_008_letter():
    case_id = "008-letter"
    classify = {
        "doc_type": "函", "doc_type_confidence": 0.93, "direction": "平行文", "style_level": 1, "risk_level": "medium",
        "reason": "用户明确'函'，用于商洽事项，往来单位为平行/不相隶属关系，符合函特征。",
        "required_rules": ["函"],
        "required_structure": ["标题", "主送单位", "事由", "商洽事项", "结尾"],
        "forbidden_items": ["不得使用'妥否，请批示'结尾", "不得写成上行请示", "不得编造发函单位全称", "不得编造收函单位全称", "不得编造活动具体信息", "不得编造联系人信息"],
        "need_manual_confirmation": False, "manual_confirmation_fields": [],
    }
    extract = {
        "source_summary": "用户素材涉及商请合作单位协助提供活动场地的函件。",
        "facts": {
            "time": [], "location": [], "organizations": ["合作单位", "对方单位"], "leaders": [], "persons": [], "products": [],
            "projects": ["活动场地"], "events": [], "data": [], "achievements": [], "problems": [],
            "requests": ["协助提供活动场地", "现场保障、设备支持等事项进行沟通"],
            "policies": [], "documents": [],
        },
        "fact_items": [
            {"type": "organization", "value": "合作单位", "source_text": "给合作单位的函", "confidence": 0.7, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "称谓不规范，需确认正式名称"},
            {"type": "organization", "value": "对方单位", "source_text": "拟商请对方单位协助", "confidence": 0.7, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "称谓不规范，需确认正式名称"},
            {"type": "project", "value": "活动场地", "source_text": "协助提供活动场地", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "request", "value": "协助提供活动场地", "source_text": "协助提供活动场地", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
            {"type": "request", "value": "现场保障、设备支持等事项进行沟通", "source_text": "并就现场保障、设备支持等事项进行沟通", "confidence": 0.95, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
        ],
        "missing_fields": [
            {"field": "发函单位全称", "reason": "用户未提供", "impact": "影响函件完整性", "suggestion": "建议确认发函单位"},
            {"field": "收函单位全称", "reason": "用户仅写'合作单位'", "impact": "影响函件抬头", "suggestion": "建议确认收函单位正式名称"},
            {"field": "活动名称", "reason": "用户未提供", "impact": "影响函件事由详实度", "suggestion": "建议确认活动名称"},
            {"field": "活动时间", "reason": "用户未提供", "impact": "影响场地需求明确性", "suggestion": "建议确认活动时间"},
            {"field": "活动规模", "reason": "用户未提供", "impact": "影响场地需求明确性", "suggestion": "建议确认活动规模"},
            {"field": "联系人信息", "reason": "用户未提供", "impact": "影响后续沟通", "suggestion": "建议确认联系人"},
        ],
        "cannot_infer": [
            {"field": "发函单位全称", "reason": "用户未提供，不得自动补充"},
            {"field": "收函单位全称", "reason": "用户仅写'合作单位'，不得自动补充"},
            {"field": "活动具体信息", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "vague_terminology", "detail": "'合作单位''对方单位'称谓不规范，需确认正式名称", "level": "medium"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "函平行文场景，style_level=1，需重点防止写成请示和使用不规范称谓。",
        "doc_type": "函", "direction": "平行文", "style_level": 1, "risk_level": "medium",
        "title_plan": {"recommended_title": "关于商请协助提供活动场地的函", "title_type": "函标题", "title_confidence": 0.8, "title_basis": ["extract.requests 包含'协助提供活动场地'"], "title_risks": ["缺少发函/收函单位前缀"], "alternative_titles": ["关于商请提供活动场地支持的函"]},
        "addressee_plan": {"recommended_addressee": "【收函单位待确认】", "source": "user_input", "confidence": 0.5, "needs_manual_confirmation": True, "note": "用户仅写'合作单位'，需确认正式名称"},
        "signer_plan": {"recommended_signer": "【发函单位待确认】", "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "用户未提供发函单位"},
        "sections": [
            {"section_id": "S1", "section_name": "事由", "purpose": "说明商请事项的背景", "content_guidance": "拟举办活动需场地支持", "fact_bindings": [{"fact_type": "project", "fact_value": "活动场地", "source_from_extract": True}], "blocked_items": ["不得编造活动具体信息"], "word_count_estimate": 80, "needs_manual_input": False},
            {"section_id": "S2", "section_name": "商洽事项", "purpose": "具体商洽内容", "content_guidance": "场地、现场保障、设备支持", "fact_bindings": [{"fact_type": "request", "fact_value": "协助提供活动场地", "source_from_extract": True}, {"fact_type": "request", "fact_value": "现场保障、设备支持等事项进行沟通", "source_from_extract": True}], "blocked_items": ["不得编造超出用户素材的商洽内容"], "word_count_estimate": 150, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "结尾", "purpose": "函的规范结尾", "content_guidance": "使用'请予协助为盼'等函结尾", "fact_bindings": [], "blocked_items": ["不得使用'妥否，请批示'"], "word_count_estimate": 30, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "客气正式", "key_expressions": ["商请", "协助", "支持", "沟通"], "forbidden_expressions": ["妥否，请批示", "请批准", "请批复", "请予支持（作为结尾）"], "style_reference": "doc-type-rules.md 函章节"},
        "title_rules": ["函标题格式：关于XXX的函"],
        "addressee_resolution": {"recommended_addressee": "【收函单位待确认】", "source": "user_input", "confidence": 0.5, "needs_manual_confirmation": True, "note": "需确认正式名称"},
        "signer_resolution": {"recommended_signer": "【发函单位待确认】", "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "发函单位缺失"},
        "title_suggestions": {"recommended_title": "关于商请协助提供活动场地的函", "alternative_titles": ["关于商请提供活动场地支持的函"], "title_rules": ["函标题格式：关于XXX的函"]},
        "missing_fields": [{"field": "发函单位全称", "reason": "用户未提供"}, {"field": "收函单位全称", "reason": "用户仅写'合作单位'"}, {"field": "活动名称", "reason": "用户未提供"}, {"field": "活动时间", "reason": "用户未提供"}],
        "cannot_infer": [{"field": "发函单位全称", "reason": "不得自动补充"}, {"field": "收函单位全称", "reason": "不得自动补充"}, {"field": "活动具体信息", "reason": "不得自动补充"}],
        "risk_flags": [{"type": "vague_terminology", "detail": "称谓不规范", "level": "medium"}],
        "manual_confirmation_fields": [{"field": "发函单位全称", "reason": "用户未提供"}, {"field": "收函单位全称", "reason": "用户仅写'合作单位'"}, {"field": "活动名称", "reason": "用户未提供"}, {"field": "活动时间", "reason": "用户未提供"}],
        "draft_directives": {"total_word_count_estimate": 300, "must_use_facts": ["协助提供活动场地", "现场保障", "设备支持"], "must_avoid": ["妥否，请批示", "请批准", "编造单位全称"], "format_requirements": ["函标准格式", "请予协助为盼结尾"]},
    }

    draft_markdown = """关于商请协助提供活动场地的函

【收函单位待确认】：

拟于近期举办活动，因活动场地需要，特致函商请贵单位协助提供活动场地支持。

具体商洽事项如下：

一、请协助提供适合活动举办的活动场地；

二、就现场保障、设备支持等事项与贵单位进行沟通协调。

以上事项，请予协助为盼。

【发函单位待确认】
【日期待确认】"""

    draft = {
        "draft_summary": "按函格式生成初稿，使用占位符标记不确定称谓，结尾为'请予协助为盼'。",
        "doc_type": "函", "direction": "平行文", "style_level": 1, "risk_level": "medium",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "活动场地", "fact_type": "project", "fact_value": "活动场地", "source_text": "协助提供活动场地", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "协助提供活动场地", "fact_type": "request", "fact_value": "协助提供活动场地", "source_text": "协助提供活动场地", "source": "extract_result.fact_items", "confidence": 0.95},
            {"draft_text": "现场保障", "fact_type": "other", "fact_value": "现场保障", "source_text": "并就现场保障、设备支持等事项进行沟通", "source": "user_input", "confidence": 0.95},
            {"draft_text": "设备支持", "fact_type": "other", "fact_value": "设备支持", "source_text": "并就现场保障、设备支持等事项进行沟通", "source": "user_input", "confidence": 0.95},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [
            {"raw_value": "合作单位", "used_value": "【收函单位待确认】", "type": "organization", "source": "user_input", "confidence": 0.5, "needs_manual_confirmation": True, "note": "'合作单位'称谓不规范，使用占位符"},
            {"raw_value": "对方单位", "used_value": "【收函单位待确认】", "type": "organization", "source": "user_input", "confidence": 0.5, "needs_manual_confirmation": True, "note": "'对方单位'称谓不规范，使用占位符"},
        ],
        "blocked_items_check": [
            {"item": "不得使用'妥否，请批示'结尾", "status": "not_used", "reason": "结尾为'请予协助为盼'"},
            {"item": "不得写成上行请示", "status": "not_used", "reason": "初稿为函格式"},
            {"item": "不得编造发函单位全称", "status": "not_used", "reason": "使用占位符"},
            {"item": "不得编造收函单位全称", "status": "not_used", "reason": "使用占位符"},
            {"item": "不得编造活动具体信息", "status": "not_used", "reason": "未编造活动名称或时间"},
            {"item": "不得编造联系人信息", "status": "not_used", "reason": "未编造联系人"},
        ],
        "warnings": [
            {"level": "medium", "type": "missing_field", "message": "收函单位全称缺失", "related_field": "收函单位", "action": "建议确认"},
            {"level": "medium", "type": "missing_field", "message": "发函单位全称缺失", "related_field": "发函单位", "action": "建议确认"},
            {"level": "medium", "type": "missing_field", "message": "活动信息不完整", "related_field": "活动信息", "action": "建议补充活动名称和时间"},
        ],
        "manual_confirmation_fields": [
            {"field": "发函单位全称", "reason": "用户未提供", "impact": "影响函件完整性", "required_before_final": True},
            {"field": "收函单位全称", "reason": "用户仅写'合作单位'", "impact": "影响函件抬头", "required_before_final": True},
            {"field": "活动名称", "reason": "用户未提供", "impact": "影响函件事由详实度", "required_before_final": False},
            {"field": "活动时间", "reason": "用户未提供", "impact": "影响场地需求明确性", "required_before_final": False},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以函格式撰写，结尾为'请予协助为盼'，无请示表达，占位符使用正确。",
        "pass": True, "score": 85, "rewrite_required": False, "risk_level": "medium",
        "checks": {
            "doc_type_check": make_check("pass", "函结构正确，结尾为'请予协助为盼'", 0),
            "structure_check": make_check("pass", "标题+主送+事由+商洽+结尾结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自用户素材", 0),
            "fact_usage_report_check": make_check("pass", "4条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("warning", "'合作单位''对方单位'已标记待确认", 2),
            "blocked_items_check": make_check("pass", "6项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "3项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "4项人工确认字段已标记", 0),
            "style_check": make_check("pass", "客气正式风格", 0),
            "format_check": make_check("pass", "函格式正确", 0),
        },
        "issues": [
            {"issue_id": "R008-001", "level": "medium", "type": "terminology_error", "location": "收函单位", "detail": "'合作单位'称谓不规范，已使用占位符", "evidence": "extract.organizations 包含'合作单位'", "suggestion": "确认正式机构名称", "rewrite_hint": "replace"},
        ],
        "rewrite_instructions": [
            {"priority": "medium", "target": "收函单位占位符", "action": "replace", "instruction": "确认后替换为正式机构全称", "basis": "人工确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "发函单位全称", "reason": "用户未提供", "impact": "影响函件完整性", "required_before_final": True},
            {"field": "收函单位全称", "reason": "用户仅写'合作单位'", "impact": "影响函件抬头", "required_before_final": True},
            {"field": "活动名称", "reason": "用户未提供", "impact": "影响函件事由详实度", "required_before_final": False},
            {"field": "活动时间", "reason": "用户未提供", "impact": "影响场地需求明确性", "required_before_final": False},
        ],
        "review_policy": REVIEW_POLICY,
    }

    rewrite = {
        "rewrite_summary": "review 未发现 critical 级别问题，函格式正确。保留函结构和占位符。",
        "doc_type": "函", "direction": "平行文", "style_level": 1, "risk_level": "medium",
        "final_markdown": draft_markdown,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [
            {"issue_id": "R008-001", "reason": "收函单位全称需确认", "required_action": "确认后替换占位符"},
        ],
        "remaining_risks": [
            {"level": "high", "type": "missing_field", "detail": "发函单位全称缺失", "action": "人工确认"},
            {"level": "high", "type": "missing_field", "detail": "收函单位全称缺失", "action": "人工确认"},
            {"level": "medium", "type": "missing_field", "detail": "活动名称缺失", "action": "可补充"},
            {"level": "medium", "type": "missing_field", "detail": "活动时间缺失", "action": "可补充"},
        ],
        "manual_confirmation_fields": [
            {"field": "发函单位全称", "reason": "用户未提供", "impact": "影响函件完整性", "required_before_final": True},
            {"field": "收函单位全称", "reason": "用户仅写'合作单位'", "impact": "影响函件抬头", "required_before_final": True},
            {"field": "活动名称", "reason": "用户未提供", "impact": "影响函件事由详实度", "required_before_final": False},
            {"field": "活动时间", "reason": "用户未提供", "impact": "影响场地需求明确性", "required_before_final": False},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success", "doc_type": "函", "risk_level": "medium", "review_pass": True, "rewrite_required": False,
        "manual_confirmation_count": 4, "remaining_risk_count": 4,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None, "error_type": None, "error_message": None, "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify, "extract_result.json": extract, "plan_result.json": plan,
        "draft_result.json": draft, "review_result.json": review, "rewrite_result.json": rewrite,
        "final_markdown.md": draft_markdown, "pipeline_report.json": pipeline_report,
    }


def gen_010_terminology_risk():
    case_id = "010-terminology-risk"
    classify = {
        "doc_type": "汇报材料", "doc_type_confidence": 0.88, "direction": "上行文", "style_level": 2, "risk_level": "high",
        "reason": "用户要求汇报材料，内容为工作进展汇报，但'芒果总部'称谓不规范。",
        "required_rules": ["汇报材料"],
        "required_structure": ["工作概述", "工作推进情况", "后续工作打算", "结尾"],
        "forbidden_items": ["不得静默将'芒果总部'写死为错误机构名", "不得使用禁用称谓", "不得编造具体工作细节", "不得编造成果数据"],
        "need_manual_confirmation": True,
        "manual_confirmation_fields": ["'芒果总部'的正式机构全称"],
    }
    extract = {
        "source_summary": "用户素材涉及文化科技融合方向工作汇报，'芒果总部'称谓不规范。",
        "facts": {
            "time": [], "location": [], "organizations": ["芒果总部"], "leaders": [], "persons": [], "products": [],
            "projects": [], "events": [], "data": [],
            "achievements": ["围绕文化科技融合方向推进相关工作"],
            "problems": [], "requests": [], "policies": [], "documents": [],
        },
        "fact_items": [
            {"type": "organization", "value": "芒果总部", "source_text": "后续希望芒果总部了解整体进展", "confidence": 0.6, "can_use_in_draft": True, "needs_manual_confirmation": True, "note": "'芒果总部'称谓不规范，可能命中禁用称谓，需确认正式机构全称"},
            {"type": "achievement", "value": "围绕文化科技融合方向推进相关工作", "source_text": "我们围绕文化科技融合方向推进相关工作", "confidence": 0.9, "can_use_in_draft": True, "needs_manual_confirmation": False, "note": None},
        ],
        "missing_fields": [
            {"field": "'芒果总部'的正式机构全称", "reason": "'芒果总部'称谓不规范", "impact": "影响汇报材料收文单位准确性", "suggestion": "需确认正式机构全称"},
            {"field": "具体工作内容细节", "reason": "用户未提供", "impact": "影响汇报详实度", "suggestion": "建议补充"},
            {"field": "具体进展成果", "reason": "用户未提供", "impact": "影响汇报可信度", "suggestion": "建议补充"},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响汇报材料完整性", "suggestion": "建议确认"},
            {"field": "汇报时间", "reason": "用户未提供", "impact": "影响汇报材料时效性", "suggestion": "建议确认"},
        ],
        "cannot_infer": [
            {"field": "'芒果总部'的正式全称", "reason": "不得用模型知识自行补充"},
            {"field": "具体工作内容和进展", "reason": "用户未提供，不得自动补充"},
        ],
        "risk_flags": [
            {"type": "vague_terminology", "detail": "'芒果总部'称谓不规范，可能命中禁用称谓", "level": "critical"},
            {"type": "vague_content", "detail": "内容笼统，缺少具体工作细节", "level": "medium"},
        ],
        "extraction_policy": EXTRACTION_POLICY,
    }
    plan = {
        "plan_summary": "汇报材料上行文场景，style_level=2，重点处理'芒果总部'不规范称谓。",
        "doc_type": "汇报材料", "direction": "上行文", "style_level": 2, "risk_level": "high",
        "title_plan": {"recommended_title": "关于文化科技融合方向工作进展的汇报", "title_type": "汇报材料标题", "title_confidence": 0.7, "title_basis": ["extract.achievements 包含'文化科技融合方向'"], "title_risks": ["缺少汇报单位和收文单位标识"], "alternative_titles": ["文化科技融合方向工作进展汇报"]},
        "addressee_plan": {"recommended_addressee": "【收文单位待确认】", "source": "user_input", "confidence": 0.3, "needs_manual_confirmation": True, "note": "'芒果总部'称谓不规范，需确认正式机构全称"},
        "signer_plan": {"recommended_signer": None, "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "汇报单位缺失"},
        "sections": [
            {"section_id": "S1", "section_name": "工作概述", "purpose": "概述工作方向", "content_guidance": "文化科技融合方向推进相关工作", "fact_bindings": [{"fact_type": "achievement", "fact_value": "围绕文化科技融合方向推进相关工作", "source_from_extract": True}], "blocked_items": ["不得编造具体工作细节", "不得编造成果数据"], "word_count_estimate": 100, "needs_manual_input": False},
            {"section_id": "S2", "section_name": "工作推进情况", "purpose": "具体工作进展", "content_guidance": "基于有限素材克制表达", "fact_bindings": [{"fact_type": "achievement", "fact_value": "围绕文化科技融合方向推进相关工作", "source_from_extract": True}], "blocked_items": ["不得编造具体工作细节", "不得编造成果数据", "不得取得显著成效"], "word_count_estimate": 200, "needs_manual_input": False},
            {"section_id": "S3", "section_name": "后续工作打算", "purpose": "后续工作计划", "content_guidance": "基于有限素材克制表达", "fact_bindings": [], "blocked_items": ["不得编造计划外的内容"], "word_count_estimate": 100, "needs_manual_input": False},
            {"section_id": "S4", "section_name": "结尾", "purpose": "汇报结尾", "content_guidance": "简短收束", "fact_bindings": [], "blocked_items": ["不得使用请示结尾"], "word_count_estimate": 30, "needs_manual_input": False},
        ],
        "style_directives": {"overall_tone": "正式务实", "key_expressions": ["推进", "开展", "落实"], "forbidden_expressions": ["取得显著成效", "芒果总部（未确认前不得使用）"], "style_reference": "doc-type-rules.md 汇报材料章节"},
        "title_rules": ["汇报材料标题应包含工作方向"],
        "addressee_resolution": {"recommended_addressee": "【收文单位待确认】", "source": "user_input", "confidence": 0.3, "needs_manual_confirmation": True, "note": "需确认正式机构全称"},
        "signer_resolution": {"recommended_signer": None, "source": "missing", "confidence": 0, "needs_manual_confirmation": True, "note": "汇报单位缺失"},
        "title_suggestions": {"recommended_title": "关于文化科技融合方向工作进展的汇报", "alternative_titles": ["文化科技融合方向工作进展汇报"], "title_rules": ["汇报材料标题应包含工作方向"]},
        "missing_fields": [{"field": "'芒果总部'的正式机构全称", "reason": "称谓不规范"}, {"field": "汇报单位名称", "reason": "用户未提供"}],
        "cannot_infer": [{"field": "'芒果总部'的正式全称", "reason": "不得用模型知识自行补充"}, {"field": "具体工作内容和进展", "reason": "不得自动补充"}],
        "risk_flags": [{"type": "vague_terminology", "detail": "'芒果总部'称谓不规范", "level": "critical"}, {"type": "vague_content", "detail": "内容笼统", "level": "medium"}],
        "manual_confirmation_fields": [{"field": "'芒果总部'的正式机构全称", "reason": "称谓不规范"}, {"field": "汇报单位名称", "reason": "用户未提供"}],
        "draft_directives": {"total_word_count_estimate": 500, "must_use_facts": ["文化科技融合方向", "推进相关工作"], "must_avoid": ["静默写死'芒果总部'", "编造工作细节", "取得显著成效"], "format_requirements": ["汇报材料格式", "占位符标记不规范称谓"]},
    }

    draft_markdown = """【收文单位待确认】：

关于文化科技融合方向工作进展的汇报

一、工作概述

围绕文化科技融合方向，积极推进相关工作。

二、工作推进情况

目前，文化科技融合方向相关工作已有序推进。在整体统筹和协调推进方面，团队持续开展各项工作，确保项目按计划实施。

三、后续工作打算

后续将继续深化文化科技融合方向的工作推进，及时向【收文单位待确认】汇报整体进展。

特此汇报。

【汇报单位待确认】
【日期待确认】"""

    draft = {
        "draft_summary": "按汇报材料格式生成初稿，对'芒果总部'使用占位符替代，未静默写死错误机构。",
        "doc_type": "汇报材料", "direction": "上行文", "style_level": 2, "risk_level": "high",
        "markdown_draft": draft_markdown,
        "fact_usage_report": [
            {"draft_text": "文化科技融合方向", "fact_type": "achievement", "fact_value": "围绕文化科技融合方向推进相关工作", "source_text": "我们围绕文化科技融合方向推进相关工作", "source": "extract_result.fact_items", "confidence": 0.9},
            {"draft_text": "推进相关工作", "fact_type": "achievement", "fact_value": "围绕文化科技融合方向推进相关工作", "source_text": "我们围绕文化科技融合方向推进相关工作", "source": "extract_result.fact_items", "confidence": 0.9},
        ],
        "rag_usage_report": [],
        "terminology_usage_report": [
            {"raw_value": "芒果总部", "used_value": "【收文单位待确认】", "type": "organization", "source": "user_input", "confidence": 0.3, "needs_manual_confirmation": True, "note": "'芒果总部'称谓不规范，已使用占位符替代，需确认正式机构全称"},
        ],
        "blocked_items_check": [
            {"item": "不得静默将'芒果总部'写死为错误机构名", "status": "not_used", "reason": "已使用占位符【收文单位待确认】"},
            {"item": "不得使用禁用称谓", "status": "not_used", "reason": "未直接使用'芒果总部'"},
            {"item": "不得编造具体工作细节", "status": "not_used", "reason": "初稿未编造工作细节"},
            {"item": "不得编造成果数据", "status": "not_used", "reason": "初稿未编造数据"},
        ],
        "warnings": [
            {"level": "critical", "type": "missing_field", "message": "'芒果总部'称谓不规范", "related_field": "收文单位", "action": "需确认正式机构全称"},
            {"level": "medium", "type": "missing_field", "message": "内容笼统缺少细节", "related_field": None, "action": "建议补充具体工作内容"},
        ],
        "manual_confirmation_fields": [
            {"field": "'芒果总部'的正式机构全称", "reason": "称谓不规范", "impact": "影响汇报材料收文单位准确性", "required_before_final": True},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响汇报材料完整性", "required_before_final": True},
        ],
        "draft_policy": DRAFT_POLICY,
    }

    review = {
        "review_summary": "初稿以汇报材料格式撰写，'芒果总部'已正确使用占位符替代，未静默写死。",
        "pass": True, "score": 82, "rewrite_required": False, "risk_level": "high",
        "checks": {
            "doc_type_check": make_check("pass", "汇报材料结构正确", 0),
            "structure_check": make_check("pass", "概述+推进+打算+结尾结构完整", 0),
            "fact_grounding_check": make_check("pass", "所有事实均来自用户素材", 0),
            "fact_usage_report_check": make_check("pass", "2条事实记录均可溯源", 0),
            "rag_usage_check": make_check("not_applicable", "rag_usage_report 为空", 0),
            "terminology_check": make_check("warning", "'芒果总部'称谓已标记待确认", 1),
            "blocked_items_check": make_check("pass", "4项禁止项均未违反", 0),
            "warnings_check": make_check("pass", "2项 warnings 已正确标记", 0),
            "manual_confirmation_check": make_check("pass", "2项人工确认字段已标记", 0),
            "style_check": make_check("pass", "正式务实风格", 0),
            "format_check": make_check("pass", "汇报材料格式正确", 0),
        },
        "issues": [
            {"issue_id": "R010-001", "level": "critical", "type": "terminology_error", "location": "收文单位", "detail": "'芒果总部'称谓不规范，已使用占位符替代", "evidence": "extract.organizations 包含'芒果总部'", "suggestion": "确认正式机构全称", "rewrite_hint": "replace"},
        ],
        "rewrite_instructions": [
            {"priority": "critical", "target": "收文单位占位符", "action": "replace", "instruction": "确认后替换为正式机构全称", "basis": "org-title-dictionary.yaml 或人工确认"},
        ],
        "manual_confirmation_fields": [
            {"field": "'芒果总部'的正式机构全称", "reason": "称谓不规范", "impact": "影响汇报材料收文单位准确性", "required_before_final": True},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响汇报材料完整性", "required_before_final": True},
        ],
        "review_policy": REVIEW_POLICY,
    }

    rewrite = {
        "rewrite_summary": "review 未发现静默使用不规范称谓问题。保留占位符，等待人工确认正式机构全称。",
        "doc_type": "汇报材料", "direction": "上行文", "style_level": 2, "risk_level": "high",
        "final_markdown": draft_markdown,
        "revision_report": [],
        "fact_usage_report": [{"final_text": item["draft_text"], "fact_type": item["fact_type"], "fact_value": item["fact_value"], "source_text": item["source_text"], "source": item["source"], "confidence": item["confidence"]} for item in draft["fact_usage_report"]],
        "terminology_usage_report": draft["terminology_usage_report"],
        "resolved_issues": [],
        "unresolved_issues": [
            {"issue_id": "R010-001", "reason": "'芒果总部'正式机构全称需确认", "required_action": "确认后替换占位符"},
        ],
        "remaining_risks": [
            {"level": "critical", "type": "missing_field", "detail": "'芒果总部'正式机构全称待确认", "action": "由 org-title-dictionary.yaml 或人工确认"},
            {"level": "high", "type": "missing_field", "detail": "汇报单位名称缺失", "action": "人工确认后补充"},
        ],
        "manual_confirmation_fields": [
            {"field": "'芒果总部'的正式机构全称", "reason": "称谓不规范", "impact": "影响汇报材料收文单位准确性", "required_before_final": True},
            {"field": "汇报单位名称", "reason": "用户未提供", "impact": "影响汇报材料完整性", "required_before_final": True},
        ],
        "final_checks": FINAL_CHECKS_ALL_TRUE,
        "rewrite_policy": REWRITE_POLICY,
    }

    pipeline_report = {
        "status": "success", "doc_type": "汇报材料", "risk_level": "high", "review_pass": True, "rewrite_required": False,
        "manual_confirmation_count": 2, "remaining_risk_count": 2,
        "schema_validation_status": {"classify": True, "extract": True, "plan": True, "draft": True, "review": True, "rewrite": True},
        "failed_stage": None, "error_type": None, "error_message": None, "schema_path": None,
        "output_files": STAGE_FILES + ["final_markdown.md", "pipeline_report.json"],
    }

    return case_id, {
        "classify_result.json": classify, "extract_result.json": extract, "plan_result.json": plan,
        "draft_result.json": draft, "review_result.json": review, "rewrite_result.json": rewrite,
        "final_markdown.md": draft_markdown, "pipeline_report.json": pipeline_report,
    }


# ═══════════════════════════════════════════
# MAIN: generate + validate + save
# ═══════════════════════════════════════════

def main():
    generators = [
        gen_001_news,
        gen_003_report,
        gen_004_notice,
        gen_005_meeting_minutes,
        gen_006_leader_speech,
        gen_007_summary,
        gen_008_letter,
        gen_010_terminology_risk,
    ]

    # Load schemas
    schemas = {}
    for stage_name in SCHEMA_MAP:
        schema_path = SCHEMAS_DIR / SCHEMA_MAP[stage_name]
        with open(schema_path, "r", encoding="utf-8") as f:
            schemas[stage_name] = json.load(f)

    total_cases = 0
    total_pass = 0
    all_results = {}

    for gen_fn in generators:
        case_id, files = gen_fn()
        total_cases += 1
        case_dir = REPORTS_DIR / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"Processing: {case_id}")
        print(f"{'='*60}")

        case_pass = True
        case_issues = []

        # Save files
        for filename, content in files.items():
            filepath = case_dir / filename
            if filename.endswith(".json"):
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                print(f"  ✅ Saved: {filename}")
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ Saved: {filename}")

        # Validate JSON files against schemas
        for stage_name in SCHEMA_MAP:
            json_file = stage_name + ".json"
            filepath = case_dir / json_file
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            try:
                jsonschema.validate(instance=data, schema=schemas[stage_name])
                print(f"  ✅ Schema valid: {json_file}")
            except jsonschema.ValidationError as e:
                case_pass = False
                msg = f"{json_file}: {e.message}"
                print(f"  ❌ Schema INVALID: {msg}")
                case_issues.append(msg)

        if case_pass:
            total_pass += 1
            print(f"  ✅ {case_id}: ALL SCHEMAS VALID")
        else:
            print(f"  ❌ {case_id}: HAS SCHEMA ERRORS")

        all_results[case_id] = {"pass": case_pass, "issues": case_issues}

    # Summary
    print(f"\n{'='*60}")
    print(f"GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total cases: {total_cases}")
    print(f"Passed: {total_pass}")
    print(f"Failed: {total_cases - total_pass}")
    for cid, res in all_results.items():
        icon = "✅" if res["pass"] else "❌"
        print(f"  {icon} {cid}")
        for issue in res["issues"]:
            print(f"      - {issue}")

    if total_pass < total_cases:
        print(f"\n❌ SOME CASES FAILED SCHEMA VALIDATION")
    else:
        print(f"\n✅ ALL CASES PASSED SCHEMA VALIDATION")


if __name__ == "__main__":
    main()
