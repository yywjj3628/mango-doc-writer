#!/usr/bin/env python3
"""
test_expansion_fixtures.py — v0.1.4 阶段 2 测试 fixtures

测试 Prompt/Schema 一致性，验证三种模式的输出结构。
"""

import json
import os
import sys
import unittest

# 将 pipeline 目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

from schema_loader import load_schema, validate_result


# ─── Fixture A: safe_official 输出 ─────────────────────────────────────────

SAFE_OFFICIAL_DRAFT = {
    "draft_summary": "按 safe_official 模式生成初稿，严格使用 extract 事实，无扩写。",
    "doc_type": "新闻稿",
    "direction": "对外宣传",
    "style_level": 3,
    "risk_level": "low",
    "markdown_draft": "# 文化科技融合创新活动在马栏山举行\n\n5月20日，文化科技融合创新活动在马栏山举行。活动现场发布三项创新成果。",
    "fact_usage_report": [
        {"draft_text": "5月20日", "fact_type": "time", "fact_value": "5月20日",
         "source_text": "5月20日", "source": "extract_result.fact_items", "confidence": 0.99}
    ],
    "rag_usage_report": [],
    "terminology_usage_report": [],
    "blocked_items_check": [
        {"item": "领导出席", "status": "not_used", "reason": "未提供"}
    ],
    "warnings": [],
    "manual_confirmation_fields": [],
    "draft_policy": {
        "body_generated": True,
        "no_new_facts": True,
        "use_only_extract_facts": True,
        "rag_used_for_style_only": True,
        "follow_plan_structure": True,
        "follow_doc_type_rules": True,
        "follow_org_title_dictionary": True
    },
    # v0.1.4 新增字段
    "generation_mode": "safe_official",
    "expansion_report": {
        "style_expansion": [],
        "structure_expansion": [],
        "rhetoric_expansion": [],
        "policy_phrase_expansion": [],
        "leadership_style_expansion": [],
        "confirmation_required": [],
        "unsafe_expansion_warnings": []
    },
    "official_use_allowed": True,
    "draft_disclaimer": None,
    "expansion_policy": {
        "no_specific_fact_fabrication": True,
        "rag_style_only": True,
        "expansion_labeled": True
    }
}

# ─── Fixture B: assisted_expansion 输出 ────────────────────────────────────

ASSISTED_EXPANSION_DRAFT = {
    "draft_summary": "按 assisted_expansion 模式生成初稿，补充了芒果系风格表达和结构骨架。",
    "doc_type": "新闻稿",
    "direction": "对外宣传",
    "style_level": 3,
    "risk_level": "low",
    "markdown_draft": "# 融合创新 智领未来——文化科技融合创新活动在马栏山举行\n\n5月20日，文化科技融合创新活动在马栏山举行。活动现场发布三项创新成果。\n\n活动进一步推动了文化科技深度融合，为芒果生态注入新动能。",
    "fact_usage_report": [
        {"draft_text": "5月20日", "fact_type": "time", "fact_value": "5月20日",
         "source_text": "5月20日", "source": "extract_result.fact_items", "confidence": 0.99}
    ],
    "rag_usage_report": [],
    "terminology_usage_report": [],
    "blocked_items_check": [],
    "warnings": [
        {"level": "medium", "type": "expansion_confirmation",
         "message": "意义价值段为系统扩写，需人工确认", "related_field": "意义价值",
         "action": "请确认活动是否确实推动了文化科技深度融合"}
    ],
    "manual_confirmation_fields": [
        {"field": "意义价值段", "reason": "系统补充的活动意义需人工确认",
         "impact": "影响材料准确性", "required_before_final": True}
    ],
    "draft_policy": {
        "body_generated": True,
        "no_new_facts": True,
        "use_only_extract_facts": True,
        "rag_used_for_style_only": True,
        "follow_plan_structure": True,
        "follow_doc_type_rules": True,
        "follow_org_title_dictionary": True,
        "generation_mode": "assisted_expansion",
        "expansion_allowed": True,
        "expansion_boundary": "style_and_structure_only",
        "all_expansions_labeled": True
    },
    # v0.1.4 新增字段
    "generation_mode": "assisted_expansion",
    "expansion_report": {
        "style_expansion": [
            {"text": "融合创新 智领未来", "description": "芒果系新闻稿标题风格，对仗式"}
        ],
        "structure_expansion": [
            {"text": "活动进一步推动了文化科技深度融合，为芒果生态注入新动能",
             "description": "补充新闻稿意义价值段骨架"}
        ],
        "rhetoric_expansion": [],
        "policy_phrase_expansion": [
            {"text": "文化科技深度融合", "description": "通用战略语汇"},
            {"text": "芒果生态", "description": "芒果体系战略表达"}
        ],
        "leadership_style_expansion": [],
        "confirmation_required": [
            {"text": "活动进一步推动了文化科技深度融合",
             "reason": "活动具体影响需人工确认"}
        ],
        "unsafe_expansion_warnings": []
    },
    "official_use_allowed": "requires_human_confirmation",
    "draft_disclaimer": None,
    "expansion_policy": {
        "no_specific_fact_fabrication": True,
        "rag_style_only": True,
        "expansion_labeled": True
    }
}

# ─── Fixture C: creative_mimic 输出 ───────────────────────────────────────

CREATIVE_MIMIC_DRAFT = {
    "draft_summary": "按 creative_mimic 模式生成内部灵感稿，包含更强风格仿写。",
    "doc_type": "新闻稿",
    "direction": "对外宣传",
    "style_level": 3,
    "risk_level": "low",
    "markdown_draft": "# 融创新之势 启未来之局——文化科技融合创新活动在马栏山举行\n\n⚠️ 本文为内部灵感稿，仅供参考。正式使用前需人工全面审核。\n\n5月20日，文化科技融合创新活动在马栏山举行。活动现场发布三项创新成果。\n\n活动以文化为魂、科技为翼，擘画了芒果生态融合创新的新蓝图。",
    "fact_usage_report": [
        {"draft_text": "5月20日", "fact_type": "time", "fact_value": "5月20日",
         "source_text": "5月20日", "source": "extract_result.fact_items", "confidence": 0.99}
    ],
    "rag_usage_report": [],
    "terminology_usage_report": [],
    "blocked_items_check": [],
    "warnings": [],
    "manual_confirmation_fields": [],
    "draft_policy": {
        "body_generated": True,
        "no_new_facts": True,
        "use_only_extract_facts": True,
        "rag_used_for_style_only": True,
        "follow_plan_structure": True,
        "follow_doc_type_rules": True,
        "follow_org_title_dictionary": True,
        "generation_mode": "creative_mimic",
        "expansion_allowed": True,
        "expansion_boundary": "full_style_mimic",
        "all_expansions_labeled": True
    },
    # v0.1.4 新增字段
    "generation_mode": "creative_mimic",
    "expansion_report": {
        "style_expansion": [
            {"text": "融创新之势 启未来之局", "description": "芒果系品牌标题风格，对仗式"},
            {"text": "以文化为魂、科技为翼", "description": "芒果系品牌表达"}
        ],
        "structure_expansion": [
            {"text": "擘画了芒果生态融合创新的新蓝图",
             "description": "补充文章收束句"}
        ],
        "rhetoric_expansion": [
            {"text": "擘画", "description": "芒果系正式修辞"}
        ],
        "policy_phrase_expansion": [
            {"text": "芒果生态", "description": "芒果体系战略表达"}
        ],
        "leadership_style_expansion": [],
        "confirmation_required": [],
        "unsafe_expansion_warnings": []
    },
    "official_use_allowed": False,
    "draft_disclaimer": "⚠️ 本文为内部灵感稿，仅供参考。正式使用前需人工全面审核。",
    "expansion_policy": {
        "no_specific_fact_fabrication": True,
        "rag_style_only": True,
        "expansion_labeled": True
    }
}

# ─── Fixture D: unsafe fabrication (review 输出) ──────────────────────────

REVIEW_WITH_UNSAFE_EXPANSION = {
    "review_summary": "draft 存在危险虚构扩写：编造了领导出席信息。",
    "pass": False,
    "score": 55,
    "rewrite_required": True,
    "risk_level": "critical",
    "checks": {
        "doc_type_check": {"status": "pass", "summary": "文种正确", "issues_count": 0},
        "structure_check": {"status": "pass", "summary": "结构正确", "issues_count": 0},
        "fact_grounding_check": {"status": "fail", "summary": "发现编造领导出席", "issues_count": 1},
        "fact_usage_report_check": {"status": "pass", "summary": "", "issues_count": 0},
        "rag_usage_check": {"status": "pass", "summary": "", "issues_count": 0},
        "terminology_check": {"status": "pass", "summary": "", "issues_count": 0},
        "blocked_items_check": {"status": "fail", "summary": "领导出席被无依据写入", "issues_count": 1},
        "warnings_check": {"status": "pass", "summary": "", "issues_count": 0},
        "manual_confirmation_check": {"status": "pass", "summary": "", "issues_count": 0},
        "style_check": {"status": "pass", "summary": "", "issues_count": 0},
        "format_check": {"status": "pass", "summary": "", "issues_count": 0}
    },
    "issues": [
        {
            "issue_id": "R001",
            "level": "critical",
            "type": "unsafe_expansion",
            "location": "markdown_draft 第2段",
            "detail": "正文出现'公司领导班子成员出席'，但 extract_result 未提供领导出席信息，属于危险虚构。",
            "evidence": "公司领导班子成员出席",
            "suggestion": "删除领导出席信息。",
            "rewrite_hint": "删除'公司领导班子成员出席'，改为中性表述。"
        }
    ],
    "rewrite_instructions": [
        {
            "priority": "critical",
            "target": "markdown_draft 第2段",
            "action": "delete_or_replace",
            "instruction": "删除'公司领导班子成员出席'，改为不涉及具体人物的中性表述。",
            "basis": "extract_result.fact_items（无领导出席）"
        }
    ],
    "manual_confirmation_fields": [],
    "review_policy": {
        "no_body_generation": True,
        "no_rewrite": True,
        "no_new_facts": True,
        "no_rag_call": True,
        "check_fact_grounding": True,
        "check_doc_type_rules": True,
        "check_org_title_dictionary": True
    },
    # v0.1.4 新增字段
    "generation_mode": "assisted_expansion",
    "official_use_allowed": "requires_human_confirmation",
    "expansion_review": {
        "status": "fail",
        "summary": "发现 1 处危险虚构：编造领导出席信息",
        "acceptable_expansion": [
            {"text": "芒果系风格表达", "type": "style_expansion"}
        ],
        "unsafe_fabrication": [
            {"text": "公司领导班子成员出席", "reason": "extract_result 未提供领导出席信息"}
        ],
        "confirmation_required": [],
        "expansion_rewrite_instructions": [
            {"target": "markdown_draft 第2段", "action": "delete",
             "instruction": "删除'公司领导班子成员出席'"}
        ]
    }
}


class TestDraftSchemaFixtures(unittest.TestCase):
    """测试 draft schema 与 fixtures 一致性"""

    def test_safe_official_draft_validates(self):
        """A. safe_official 输出通过 schema 校验"""
        validate_result("draft", SAFE_OFFICIAL_DRAFT)

    def test_assisted_expansion_draft_validates(self):
        """B. assisted_expansion 输出通过 schema 校验"""
        validate_result("draft", ASSISTED_EXPANSION_DRAFT)

    def test_creative_mimic_draft_validates(self):
        """C. creative_mimic 输出通过 schema 校验"""
        validate_result("draft", CREATIVE_MIMIC_DRAFT)

    def test_safe_official_expansion_report_empty(self):
        """A. safe_official 扩写报告为空"""
        report = SAFE_OFFICIAL_DRAFT["expansion_report"]
        for key in report:
            self.assertEqual(len(report[key]), 0, f"safe_official expansion_report.{key} should be empty")

    def test_safe_official_official_use_allowed_true(self):
        """A. safe_official official_use_allowed=True"""
        self.assertTrue(SAFE_OFFICIAL_DRAFT["official_use_allowed"])

    def test_assisted_expansion_has_expansions(self):
        """B. assisted_expansion 有扩写内容"""
        report = ASSISTED_EXPANSION_DRAFT["expansion_report"]
        self.assertTrue(len(report["style_expansion"]) > 0)
        self.assertTrue(len(report["structure_expansion"]) > 0)
        self.assertTrue(len(report["confirmation_required"]) > 0)

    def test_assisted_expansion_official_use_requires_confirmation(self):
        """B. assisted_expansion official_use_allowed=requires_human_confirmation"""
        self.assertEqual(ASSISTED_EXPANSION_DRAFT["official_use_allowed"], "requires_human_confirmation")

    def test_creative_mimic_has_disclaimer(self):
        """C. creative_mimic 有 draft_disclaimer"""
        self.assertIsNotNone(CREATIVE_MIMIC_DRAFT["draft_disclaimer"])
        self.assertIn("灵感稿", CREATIVE_MIMIC_DRAFT["draft_disclaimer"])

    def test_creative_mimic_official_use_allowed_false(self):
        """C. creative_mimic official_use_allowed=False"""
        self.assertFalse(CREATIVE_MIMIC_DRAFT["official_use_allowed"])

    def test_no_specific_fact_fabrication_all_modes(self):
        """所有模式 no_specific_fact_fabrication=True"""
        for fixture in [SAFE_OFFICIAL_DRAFT, ASSISTED_EXPANSION_DRAFT, CREATIVE_MIMIC_DRAFT]:
            self.assertTrue(fixture["expansion_policy"]["no_specific_fact_fabrication"])


class TestReviewSchemaFixtures(unittest.TestCase):
    """测试 review schema 与 fixtures 一致性"""

    def test_review_with_unsafe_expansion_validates(self):
        """D. 含 unsafe_expansion 的 review 输出通过 schema 校验"""
        validate_result("review", REVIEW_WITH_UNSAFE_EXPANSION)

    def test_unsafe_expansion_is_critical(self):
        """D. unsafe_expansion 为 critical 级别"""
        issues = REVIEW_WITH_UNSAFE_EXPANSION["issues"]
        unsafe = [i for i in issues if i["type"] == "unsafe_expansion"]
        self.assertTrue(len(unsafe) > 0)
        self.assertEqual(unsafe[0]["level"], "critical")

    def test_expansion_review_status_fail(self):
        """D. expansion_review status 为 fail"""
        self.assertEqual(REVIEW_WITH_UNSAFE_EXPANSION["expansion_review"]["status"], "fail")

    def test_rewrite_required_true(self):
        """D. 存在 unsafe_expansion 时 rewrite_required=True"""
        self.assertTrue(REVIEW_WITH_UNSAFE_EXPANSION["rewrite_required"])


class TestSchemaBackwardCompatibility(unittest.TestCase):
    """测试 schema 向后兼容（v0.1.3 无新增字段的 fixture 仍能通过）"""

    def test_minimal_draft_validates(self):
        """最小 draft fixture（无 v0.1.4 新增字段）应能通过"""
        minimal_draft = {
            "draft_summary": "test",
            "doc_type": "新闻稿",
            "direction": "对外宣传",
            "style_level": 3,
            "risk_level": "low",
            "markdown_draft": "# test\n\ntest content",
            "fact_usage_report": [],
            "rag_usage_report": [],
            "terminology_usage_report": [],
            "blocked_items_check": [],
            "warnings": [],
            "manual_confirmation_fields": [],
            "draft_policy": {
                "body_generated": True,
                "no_new_facts": True,
                "use_only_extract_facts": True,
                "rag_used_for_style_only": True,
                "follow_plan_structure": True,
                "follow_doc_type_rules": True,
                "follow_org_title_dictionary": True
            }
        }
        validate_result("draft", minimal_draft)

    def test_minimal_review_validates(self):
        """最小 review fixture（无 v0.1.4 新增字段）应能通过"""
        minimal_review = {
            "review_summary": "test",
            "pass": True,
            "score": 90,
            "rewrite_required": False,
            "risk_level": "low",
            "checks": {
                "doc_type_check": {"status": "pass", "summary": "", "issues_count": 0},
                "structure_check": {"status": "pass", "summary": "", "issues_count": 0},
                "fact_grounding_check": {"status": "pass", "summary": "", "issues_count": 0},
                "fact_usage_report_check": {"status": "pass", "summary": "", "issues_count": 0},
                "rag_usage_check": {"status": "pass", "summary": "", "issues_count": 0},
                "terminology_check": {"status": "pass", "summary": "", "issues_count": 0},
                "blocked_items_check": {"status": "pass", "summary": "", "issues_count": 0},
                "warnings_check": {"status": "pass", "summary": "", "issues_count": 0},
                "manual_confirmation_check": {"status": "pass", "summary": "", "issues_count": 0},
                "style_check": {"status": "pass", "summary": "", "issues_count": 0},
                "format_check": {"status": "pass", "summary": "", "issues_count": 0}
            },
            "issues": [],
            "rewrite_instructions": [],
            "manual_confirmation_fields": [],
            "review_policy": {
                "no_body_generation": True,
                "no_rewrite": True,
                "no_new_facts": True,
                "no_rag_call": True,
                "check_fact_grounding": True,
                "check_doc_type_rules": True,
                "check_org_title_dictionary": True
            }
        }
        validate_result("review", minimal_review)


class TestPlanSchemaExpansionFields(unittest.TestCase):
    """测试 plan schema 扩展字段"""

    def test_plan_with_expansion_directives_validates(self):
        """plan 含 controlled_expansion_directives 通过 schema 校验"""
        # 加载 plan fixture
        fixture_path = os.path.join(
            os.path.dirname(__file__), "..", "tests", "fixtures", "001-news",
            "plan_result.json"
        )
        if os.path.exists(fixture_path):
            with open(fixture_path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
            # 添加 v0.1.4 字段
            plan_data["generation_mode"] = "assisted_expansion"
            plan_data["expansion_boundaries"] = {
                "mode": "assisted_expansion",
                "expansion_enabled": True,
                "no_specific_fact_fabrication": True,
                "rag_style_only": True,
                "all_expansions_labeled": True
            }
            plan_data["draft_directives"]["controlled_expansion_directives"] = {
                "allowed_expansions": ["structure_skeleton", "transition_sentences"],
                "must_mark_confirmation": ["inferred_business_background"],
                "forbidden_expansions": ["specific_leader_names", "specific_data"]
            }
            validate_result("plan", plan_data)


class TestQualityScoreSchemaExpansionFields(unittest.TestCase):
    """测试 quality_score schema 扩展字段"""

    def test_quality_score_with_expansion_validates(self):
        """quality_score 含扩写字段通过 schema 校验"""
        fixture_path = os.path.join(
            os.path.dirname(__file__), "..", "tests", "fixtures", "001-news",
            "quality_score_result.json"
        )
        if os.path.exists(fixture_path):
            with open(fixture_path, "r", encoding="utf-8") as f:
                qs_data = json.load(f)
            # 添加 v0.1.4 字段
            qs_data["generation_mode"] = "assisted_expansion"
            qs_data["mode_adjusted_threshold"] = 7
            qs_data["official_use_allowed"] = "requires_human_confirmation"
            qs_data["expansion_quality_check"] = {
                "status": "pass",
                "summary": "扩写内容均在安全范围内",
                "unsafe_expansion_count": 0,
                "confirmation_required_count": 2
            }
            qs_data["draft_disclaimer_check"] = {
                "status": "not_applicable",
                "detail": "非 creative_mimic 模式"
            }
            qs_data["confirmation_required_check"] = {
                "status": "warning",
                "detail": "存在 2 项需人工确认内容",
                "items": ["推断的业务背景", "推断的政策口径"]
            }
            validate_result("quality_score", qs_data)


if __name__ == "__main__":
    unittest.main()
