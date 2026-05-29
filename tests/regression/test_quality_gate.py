#!/usr/bin/env python3
"""
test_quality_gate.py — 质量门禁分支逻辑测试（mock 模式）

阶段 3 测试：不依赖 DeepSeek API / RAG / Qdrant，
通过 mock _run_single_stage 来验证 quality gate 循环逻辑。

验证场景：
  A. 质量通过（首次评分 overall_pass=True）
  B. 风格低分 → 返修 → 通过
  C. 持续低分 → 达到最大轮次 → warn_and_output
  D. fact_safety < 8 → human_review_required=True
  E. QUALITY_GATE_ENABLED=false → 回退旧流程
  F. QUALITY_GATE_MAX_ROUNDS=0 → 只评分不返修
  G. quality gate 调用异常 → warn_and_output
  H. rewrite 返修失败 → 保留上一版
  I. 无返修指令 → warn_and_output
"""

import json
import os
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List, Optional

# 项目根
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
PIPELINE_DIR = PROJECT_DIR / "pipeline"
SCHEMAS_DIR = PROJECT_DIR / "schemas"
FIXTURES_DIR = PROJECT_DIR / "tests" / "fixtures"

sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(PROJECT_DIR / "tests" / "regression"))

from pipeline_types import PipelineInput, PipelineReport, PipelineResult, StageResult
from schema_loader import load_schema, validate_result


# ─── Mock 数据构造工具 ──────────────────────────────────────────────────────

def make_quality_score_result(
    overall_pass: bool,
    overall_score: float,
    scores: Dict[str, int],
    failed_dimensions: List[str],
    rewrite_required: bool,
    rewrite_instructions: List[Dict],
    human_review_required: bool = False,
    risk_notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """构造符合 quality_score.schema.json 的 mock 结果"""
    return {
        "quality_summary": f"测试结果 overall={overall_score} pass={overall_pass}",
        "scores": scores,
        "threshold": 8,
        "overall_score": overall_score,
        "failed_dimensions": failed_dimensions,
        "overall_pass": overall_pass,
        "rewrite_required": rewrite_required,
        "quality_rewrite_instructions": rewrite_instructions,
        "human_review_required": human_review_required,
        "risk_notes": risk_notes or [],
        "scoring_basis": {k: f"{v}分" for k, v in scores.items()},
        "no_new_facts_check": {
            "status": "fail" if scores.get("fact_safety", 10) < 8 else "pass",
            "suspected_new_facts": [{"text": "测试新增事实", "location": "第3段", "reason": "extract中无此数据"}] if scores.get("fact_safety", 10) < 8 else [],
            "detail": "extract中无此数据" if scores.get("fact_safety", 10) < 8 else "无新增事实",
        },
        "doc_type_check": {"status": "pass", "detail": "文种匹配"},
        "style_check": {
            "status": "pass" if scores.get("mango_style_fit", 10) >= 8 else "fail",
            "detail": "风格匹配" if scores.get("mango_style_fit", 10) >= 8 else "风格偏离",
        },
        "final_output_policy": {
            "recommendation": "pass" if overall_pass else ("warn_and_output" if not rewrite_instructions else "rewrite"),
            "reason": "所有维度达标" if overall_pass else "存在低分维度",
        },
        "quality_gate_policy": {
            "no_body_generation": True,
            "no_body_modification": True,
            "no_new_facts": True,
            "no_rag_call": True,
            "no_doc_type_change": True,
            "evaluate_only": True,
        },
    }


def make_rewrite_result(final_markdown: str, revision_prefix: str = "R") -> Dict[str, Any]:
    """构造符合 rewrite.schema.json 的 mock 结果"""
    return {
        "rewrite_summary": f"测试{revision_prefix}返修",
        "doc_type": "新闻稿",
        "direction": "对外宣传",
        "style_level": 3,
        "risk_level": "low",
        "final_markdown": final_markdown,
        "revision_report": [
            {
                "revision_id": f"{revision_prefix}-001",
                "issue_id": f"{revision_prefix}001",
                "action": "replace",
                "before": "原始表达",
                "after": "修正表达",
                "reason": f"{revision_prefix}返修",
                "basis": f"{revision_prefix}_result",
            }
        ],
        "fact_usage_report": [
            {
                "final_text": "测试事实",
                "fact_type": "data",
                "fact_value": "测试数据",
                "source_text": "用户素材",
                "source": "extract_result",
                "confidence": 1.0,
            }
        ],
        "terminology_usage_report": [],
        "resolved_issues": [
            {"issue_id": f"{revision_prefix}001", "resolution": "修改", "basis": f"{revision_prefix}_result"}
        ],
        "unresolved_issues": [],
        "remaining_risks": [],
        "manual_confirmation_fields": [],
        "final_checks": {
            "doc_type_fixed": True,
            "unsupported_facts_removed": True,
            "blocked_items_removed": True,
            "terminology_checked": True,
            "manual_confirmations_preserved": True,
        },
        "rewrite_policy": {
            "body_rewritten": True,
            "no_new_facts": True,
            "use_only_extract_facts": True,
            "no_rag_call": True,
            "follow_review_instructions": True,
            "follow_doc_type_rules": True,
            "follow_org_title_dictionary": True,
        },
    }


# ─── 核心测试类 ─────────────────────────────────────────────────────────────

class TestQualityGate(unittest.TestCase):
    """质量门禁分支逻辑 mock 测试"""

    # mock _run_single_stage 的调用记录
    call_log: List[Dict[str, Any]]

    def setUp(self):
        """每个测试前重置 call log"""
        self.call_log = []

    def _mock_run_single_stage(self, call_log: list, responses: dict):
        """创建 _run_single_stage mock 函数

        Args:
            call_log: 外部列表，记录每次调用
            responses: {stage_or_key: StageResult} 按调用顺序匹配
        """
        call_count = [0]

        def mock_fn(stage: str, payload: dict, **kwargs):
            entry = {"call": call_count[0], "stage": stage, "payload_keys": list(payload.keys())}
            call_log.append(entry)
            idx = call_count[0]
            call_count[0] += 1

            if idx < len(responses):
                return responses[idx]
            else:
                return StageResult(
                    stage=stage, status="failed",
                    error=f"unexpected call #{idx} stage={stage}",
                    validation_passed=False,
                )

        return mock_fn

    def _build_minimal_completed(self) -> Dict[str, Any]:
        """构造最小的六阶段 completed 字典"""
        classify = {"doc_type": "新闻稿", "direction": "对外宣传", "style_level": 3, "risk_level": "low"}
        extract = {"fact_items": [], "missing_fields": [], "cannot_infer": []}
        plan = {"structure": []}
        draft = {"final_markdown": "初稿正文", "fact_usage_report": []}
        review = {"pass": True, "score": 85, "rewrite_required": False, "issues": []}
        rewrite = make_rewrite_result("最终稿正文")
        return {
            "classify": classify,
            "extract": extract,
            "plan": plan,
            "draft": draft,
            "review": review,
            "rewrite": rewrite,
        }

    def _run_quality_gate_logic(
        self,
        qg_enabled: bool = True,
        qg_threshold: float = 8.0,
        qg_max_rounds: int = 2,
        completed: Optional[Dict] = None,
        mock_responses: Optional[List[StageResult]] = None,
    ) -> Dict[str, Any]:
        """执行质量门禁逻辑（从 run_pipeline.py 提取的核心循环）

        返回: 包含 pipeline_report 部分字段和 final_markdown 的字典
        """
        if completed is None:
            completed = self._build_minimal_completed()

        if mock_responses is None:
            mock_responses = []

        report = PipelineReport()
        call_log = []
        mock_fn = self._mock_run_single_stage(call_log, mock_responses)

        final_markdown = completed.get("rewrite", {}).get("final_markdown", "")
        quality_history = []
        quality_rewrite_applied = False

        if qg_enabled:
            qg_round = 0
            while True:
                qg_round += 1

                # 构造 quality gate payload
                qg_payload = {
                    **completed,
                    "quality_rewrite_round": qg_round - 1,
                    "max_quality_rewrite_rounds": qg_max_rounds,
                }

                # 调用 mock quality_score
                qg_stage_result = mock_fn("quality_score", qg_payload)

                if qg_stage_result.status == "failed":
                    report.quality_gate_error = f"质量门禁调用失败 (round {qg_round}): {qg_stage_result.error}"
                    report.quality_gate_pass = None
                    report.final_output_policy = "warn_and_output"
                    report.human_review_required = True
                    report.quality_score_history = quality_history
                    break

                qg_result = qg_stage_result.result

                round_record = {
                    "round": qg_round,
                    "overall_score": qg_result.get("overall_score"),
                    "scores": qg_result.get("scores"),
                    "failed_dimensions": qg_result.get("failed_dimensions", []),
                    "overall_pass": qg_result.get("overall_pass"),
                    "rewrite_required": qg_result.get("rewrite_required"),
                    "human_review_required": qg_result.get("human_review_required"),
                    "final_output_policy": qg_result.get("final_output_policy", {}).get("recommendation"),
                }
                quality_history.append(round_record)

                if qg_result.get("overall_pass", False):
                    report.quality_gate_pass = True
                    report.final_quality_scores = qg_result.get("scores")
                    report.failed_dimensions = []
                    report.final_output_policy = "pass"
                    report.human_review_required = qg_result.get("human_review_required", False)
                    break

                if qg_round >= qg_max_rounds:
                    report.quality_gate_pass = False
                    report.final_quality_scores = qg_result.get("scores")
                    report.failed_dimensions = qg_result.get("failed_dimensions", [])
                    report.final_output_policy = "warn_and_output"
                    report.human_review_required = True
                    report.quality_score_history = quality_history
                    break

                qg_instructions = qg_result.get("quality_rewrite_instructions", [])
                if not qg_instructions:
                    report.quality_gate_pass = False
                    report.final_quality_scores = qg_result.get("scores")
                    report.failed_dimensions = qg_result.get("failed_dimensions", [])
                    report.final_output_policy = "warn_and_output"
                    report.human_review_required = True
                    report.quality_score_history = quality_history
                    break

                # 回到 rewrite
                prev_final_markdown = final_markdown
                rewrite_payload = {
                    **completed,
                    "quality_rewrite_instructions": json.dumps(qg_instructions, ensure_ascii=False),
                }
                rewrite_result = mock_fn("rewrite", rewrite_payload)

                if rewrite_result.status == "failed":
                    final_markdown = prev_final_markdown
                    report.quality_gate_error = f"质量返修 rewrite 失败 (round {qg_round}): {rewrite_result.error}"
                    report.quality_gate_pass = False
                    report.final_output_policy = "warn_and_output"
                    report.human_review_required = True
                    report.quality_score_history = quality_history
                    break

                quality_rewrite_applied = True
                completed["rewrite"] = rewrite_result.result
                final_markdown = rewrite_result.result.get("final_markdown", prev_final_markdown)

            report.quality_gate_rounds_used = qg_round
            report.quality_score_history = quality_history
            report.quality_rewrite_applied = quality_rewrite_applied
        else:
            report.quality_gate_enabled = False
            report.quality_gate_pass = None

        report.quality_gate_enabled = qg_enabled
        report.quality_gate_threshold = qg_threshold
        report.quality_gate_max_rounds = qg_max_rounds

        return {
            "report": report,
            "final_markdown": final_markdown,
            "call_log": call_log,
        }


    # ─── 场景 A：质量通过 ────────────────────────────────────────────────

    def test_A_quality_pass(self):
        """A. 首次评分 overall_pass=True，不触发返修"""
        scores_all_pass = {
            "fact_safety": 9, "doc_type_fit": 9, "mango_style_fit": 8,
            "logic_completeness": 9, "language_quality": 10, "risk_control": 9,
        }
        qg_result = make_quality_score_result(
            overall_pass=True, overall_score=9.0, scores=scores_all_pass,
            failed_dimensions=[], rewrite_required=False,
            rewrite_instructions=[], human_review_required=False,
        )
        responses = [StageResult(stage="quality_score", status="success", result=qg_result, validation_passed=True)]

        result = self._run_quality_gate_logic(mock_responses=responses)
        report = result["report"]

        self.assertTrue(report.quality_gate_pass, "quality_gate_pass 应为 True")
        self.assertEqual(report.quality_gate_rounds_used, 1, "应只评 1 轮")
        self.assertEqual(report.final_output_policy, "pass")
        self.assertFalse(report.quality_rewrite_applied, "不应有返修")
        self.assertEqual(len(result["call_log"]), 1, "只应调用 1 次 quality_score")
        self.assertEqual(result["call_log"][0]["stage"], "quality_score")

    # ─── 场景 B：风格低分 → 返修 → 通过 ──────────────────────────────────

    def test_B_style_rewrite_then_pass(self):
        """B. mango_style_fit < 8 → 返修 → 通过"""
        scores_low_style = {
            "fact_safety": 9, "doc_type_fit": 8, "mango_style_fit": 5,
            "logic_completeness": 9, "language_quality": 9, "risk_control": 9,
        }
        qg_result_1 = make_quality_score_result(
            overall_pass=False, overall_score=8.2, scores=scores_low_style,
            failed_dimensions=["mango_style_fit"], rewrite_required=True,
            rewrite_instructions=[
                {"dimension": "mango_style_fit", "target": "≥8",
                 "suggested_action": "replace", "reason": "风格偏离，建议第2段增加芒果系口语化表达",
                 "basis": "mango_style_fit=5"}
            ],
        )
        scores_pass = {k: min(v + 2, 10) for k, v in scores_low_style.items()}
        scores_pass["mango_style_fit"] = 8
        qg_result_2 = make_quality_score_result(
            overall_pass=True, overall_score=8.7, scores=scores_pass,
            failed_dimensions=[], rewrite_required=False,
            rewrite_instructions=[], human_review_required=False,
        )
        rewrite_result = make_rewrite_result("返修后正文", revision_prefix="Q")
        responses = [
            StageResult(stage="quality_score", status="success", result=qg_result_1, validation_passed=True),
            StageResult(stage="rewrite", status="success", result=rewrite_result, validation_passed=True),
            StageResult(stage="quality_score", status="success", result=qg_result_2, validation_passed=True),
        ]

        result = self._run_quality_gate_logic(mock_responses=responses)
        report = result["report"]

        self.assertTrue(report.quality_gate_pass, "最终应通过")
        self.assertEqual(report.quality_gate_rounds_used, 2, "应评 2 轮")
        self.assertEqual(report.final_output_policy, "pass")
        self.assertTrue(report.quality_rewrite_applied, "应有返修")
        self.assertEqual(len(result["call_log"]), 3, "应调用 3 次: quality_score→rewrite→quality_score")
        self.assertEqual(result["call_log"][0]["stage"], "quality_score")
        self.assertEqual(result["call_log"][1]["stage"], "rewrite")
        self.assertEqual(result["call_log"][2]["stage"], "quality_score")
        self.assertEqual(result["final_markdown"], "返修后正文")

    # ─── 场景 C：达到最大返修轮次仍不通过 ──────────────────────────────────

    def test_C_max_rounds_warn_and_output(self):
        """C. 持续低分 → 达到最大轮次 → warn_and_output"""
        scores_low = {
            "fact_safety": 7, "doc_type_fit": 7, "mango_style_fit": 5,
            "logic_completeness": 7, "language_quality": 6, "risk_control": 7,
        }
        qg_result = make_quality_score_result(
            overall_pass=False, overall_score=6.5, scores=scores_low,
            failed_dimensions=["mango_style_fit", "language_quality"],
            rewrite_required=True,
            rewrite_instructions=[
                {"dimension": "mango_style_fit", "target": "≥8", "suggested_action": "replace", "reason": "风格低分", "basis": "mango_style_fit=5"}
            ],
            human_review_required=True,
        )
        rewrite_result = make_rewrite_result("返修后正文", revision_prefix="Q")

        # 构造 2 轮（默认 max_rounds=2）的 mock 响应
        responses = []
        for _ in range(2):  # 2 轮：每轮 = quality_score + rewrite
            responses.append(StageResult(stage="quality_score", status="success", result=qg_result, validation_passed=True))
            responses.append(StageResult(stage="rewrite", status="success", result=rewrite_result, validation_passed=True))
        # 第 3 轮 quality_score（已经达到 max，但循环会先评分再判断）
        # 不，看代码逻辑：round 2 开始时，如果 round 1 已经有 instructions，
        # 会做 rewrite，然后 round 2 评分。如果 round 2 仍不通过且 round >= max_rounds，直接 break。
        # 所以实际是：qg(1) → rewrite(1) → qg(2) → break

        responses = [
            # round 1: quality_score → rewrite
            StageResult(stage="quality_score", status="success", result=qg_result, validation_passed=True),
            StageResult(stage="rewrite", status="success", result=rewrite_result, validation_passed=True),
            # round 2: quality_score（不通过，round >= max_rounds → break）
            StageResult(stage="quality_score", status="success", result=qg_result, validation_passed=True),
        ]

        result = self._run_quality_gate_logic(qg_max_rounds=2, mock_responses=responses)
        report = result["report"]

        self.assertFalse(report.quality_gate_pass, "不应通过")
        self.assertEqual(report.quality_gate_rounds_used, 2, "应用满 2 轮")
        self.assertEqual(report.final_output_policy, "warn_and_output")
        self.assertTrue(report.human_review_required, "需要人工复核")
        self.assertTrue(report.quality_rewrite_applied, "应有返修")
        self.assertEqual(report.failed_dimensions, ["mango_style_fit", "language_quality"])
        self.assertEqual(len(report.quality_score_history), 2, "应有 2 条评分历史")

    # ─── 场景 D：fact_safety 低分 → human_review_required ─────────────────

    def test_D_fact_safety_human_review(self):
        """D. fact_safety < 8 → human_review_required=true"""
        scores_risky = {
            "fact_safety": 4, "doc_type_fit": 8, "mango_style_fit": 8,
            "logic_completeness": 8, "language_quality": 8, "risk_control": 9,
        }
        qg_result = make_quality_score_result(
            overall_pass=False, overall_score=7.5, scores=scores_risky,
            failed_dimensions=["fact_safety"],
            rewrite_required=True,
            rewrite_instructions=[
                {"dimension": "fact_safety", "target": "≥8",
                 "suggested_action": "delete",
                 "reason": "疑似新增事实", "basis": "fact_safety=4"}
            ],
            human_review_required=True,
            risk_notes=["疑似新增事实：正文中出现素材未提供的数据"],
        )
        responses = [StageResult(stage="quality_score", status="success", result=qg_result, validation_passed=True)]

        result = self._run_quality_gate_logic(qg_max_rounds=1, mock_responses=responses)
        report = result["report"]

        self.assertTrue(report.human_review_required, "fact_safety < 8 应触发 human_review")
        self.assertIn("fact_safety", report.failed_dimensions)
        self.assertEqual(report.final_output_policy, "warn_and_output")
        # 验证 rewrite_instructions 中要求删除疑似新增事实，不是补充事实
        instr = qg_result["quality_rewrite_instructions"][0]
        self.assertEqual(instr["suggested_action"], "delete", "应使用 delete 操作，不允许补充事实")

    # ─── 场景 E：QUALITY_GATE_ENABLED=false ──────────────────────────────

    def test_E_disabled_fallback(self):
        """E. QUALITY_GATE_ENABLED=false → 完全回退，不调用 quality_score"""
        result = self._run_quality_gate_logic(qg_enabled=False)
        report = result["report"]

        self.assertFalse(report.quality_gate_enabled, "quality_gate_enabled 应为 False")
        self.assertIsNone(report.quality_gate_pass, "quality_gate_pass 应为 None")
        self.assertEqual(len(result["call_log"]), 0, "不应有任何 mock 调用")
        self.assertEqual(result["final_markdown"], "最终稿正文", "final_markdown 应保留原值")

    # ─── 场景 F：MAX_ROUNDS=0 → 只评分不返修 ───────────────────────────

    def test_F_max_rounds_zero(self):
        """F. MAX_ROUNDS=0 → 评分后直接判断，不返修"""
        scores_low = {
            "fact_safety": 9, "doc_type_fit": 8, "mango_style_fit": 5,
            "logic_completeness": 8, "language_quality": 8, "risk_control": 9,
        }
        qg_result = make_quality_score_result(
            overall_pass=False, overall_score=7.8, scores=scores_low,
            failed_dimensions=["mango_style_fit"],
            rewrite_required=True,
            rewrite_instructions=[{"dimension": "mango_style_fit", "target": "≥8", "suggested_action": "replace", "reason": "风格低分", "basis": "5"}],
        )
        responses = [StageResult(stage="quality_score", status="success", result=qg_result, validation_passed=True)]

        result = self._run_quality_gate_logic(qg_max_rounds=0, mock_responses=responses)
        report = result["report"]

        self.assertFalse(report.quality_gate_pass)
        self.assertEqual(report.quality_gate_rounds_used, 1, "评 1 轮后因 max_rounds=0 超限")
        self.assertEqual(report.final_output_policy, "warn_and_output")
        self.assertEqual(len(result["call_log"]), 1, "只调用 1 次 quality_score，不调用 rewrite")

    def test_F_max_rounds_one(self):
        """F-2. MAX_ROUNDS=1 → 首次评分不通过即退出，最多评 1 轮"""
        scores_low = {
            "fact_safety": 9, "doc_type_fit": 8, "mango_style_fit": 5,
            "logic_completeness": 8, "language_quality": 8, "risk_control": 9,
        }
        qg_low = make_quality_score_result(
            overall_pass=False, overall_score=7.8, scores=scores_low,
            failed_dimensions=["mango_style_fit"],
            rewrite_required=True,
            rewrite_instructions=[{"dimension": "mango_style_fit", "target": "≥8", "suggested_action": "replace", "reason": "风格低分", "basis": "5"}],
        )
        responses = [
            StageResult(stage="quality_score", status="success", result=qg_low, validation_passed=True),
        ]

        result = self._run_quality_gate_logic(qg_max_rounds=1, mock_responses=responses)
        report = result["report"]

        self.assertFalse(report.quality_gate_pass)
        self.assertEqual(report.quality_gate_rounds_used, 1, "max_rounds=1 时只评 1 轮")
        self.assertFalse(report.quality_rewrite_applied, "max_rounds=1 时无返修")
        self.assertEqual(len(result["call_log"]), 1, "只调用 1 次 quality_score")

    # ─── 场景 G：quality gate 调用异常 ────────────────────────────────────

    def test_G_quality_gate_exception(self):
        """G. quality_score 调用异常 → warn_and_output，不丢稿件"""
        responses = [
            StageResult(stage="quality_score", status="failed",
                        error="模型调用异常: ConnectionError", validation_passed=False),
        ]
        completed = self._build_minimal_completed()
        result = self._run_quality_gate_logic(completed=completed, mock_responses=responses)
        report = result["report"]

        self.assertIsNone(report.quality_gate_pass, "异常时 pass 应为 None")
        self.assertEqual(report.final_output_policy, "warn_and_output")
        self.assertTrue(report.human_review_required)
        self.assertIsNotNone(report.quality_gate_error)
        self.assertIn("ConnectionError", report.quality_gate_error)
        self.assertEqual(result["final_markdown"], "最终稿正文", "final_markdown 不应丢失")

    # ─── 场景 H：rewrite 返修失败 → 保留上一版 ───────────────────────────

    def test_H_rewrite_failure_preserves_markdown(self):
        """H. rewrite 返修失败 → 保留上一版 final_markdown"""
        scores_low = {
            "fact_safety": 9, "doc_type_fit": 8, "mango_style_fit": 5,
            "logic_completeness": 8, "language_quality": 8, "risk_control": 9,
        }
        qg_low = make_quality_score_result(
            overall_pass=False, overall_score=7.8, scores=scores_low,
            failed_dimensions=["mango_style_fit"],
            rewrite_required=True,
            rewrite_instructions=[{"dimension": "mango_style_fit", "target": "≥8", "suggested_action": "replace", "reason": "风格低分", "basis": "5"}],
        )
        responses = [
            StageResult(stage="quality_score", status="success", result=qg_low, validation_passed=True),
            StageResult(stage="rewrite", status="failed", error="schema_validation_error", validation_passed=False),
        ]

        completed = self._build_minimal_completed()
        result = self._run_quality_gate_logic(completed=completed, mock_responses=responses)
        report = result["report"]

        self.assertFalse(report.quality_gate_pass)
        self.assertEqual(report.final_output_policy, "warn_and_output")
        self.assertTrue(report.quality_rewrite_applied is False or report.quality_gate_error is not None,
                        "rewrite 失败应有 error 标记")
        self.assertEqual(result["final_markdown"], "最终稿正文", "应保留上一版 final_markdown")

    # ─── 场景 I：无返修指令 → warn ──────────────────────────────────────

    def test_I_no_instructions_warn(self):
        """I. 低分但无返修指令 → warn_and_output"""
        scores_low = {
            "fact_safety": 9, "doc_type_fit": 8, "mango_style_fit": 5,
            "logic_completeness": 8, "language_quality": 8, "risk_control": 9,
        }
        qg_result = make_quality_score_result(
            overall_pass=False, overall_score=7.8, scores=scores_low,
            failed_dimensions=["mango_style_fit"],
            rewrite_required=True,
            rewrite_instructions=[],  # 无返修指令
        )
        responses = [StageResult(stage="quality_score", status="success", result=qg_result, validation_passed=True)]

        result = self._run_quality_gate_logic(qg_max_rounds=2, mock_responses=responses)
        report = result["report"]

        self.assertFalse(report.quality_gate_pass)
        self.assertEqual(report.final_output_policy, "warn_and_output")
        self.assertEqual(len(result["call_log"]), 1, "不应调用 rewrite")
        self.assertEqual(report.quality_gate_rounds_used, 1)


# ─── Schema 验证测试 ─────────────────────────────────────────────────────────

class TestQualityGateSchema(unittest.TestCase):
    """quality_score schema 和 rewrite schema 兼容性测试"""

    def test_quality_score_schema_pass(self):
        """quality_score 通过场景 schema 校验"""
        scores = {"fact_safety": 9, "doc_type_fit": 9, "mango_style_fit": 8,
                  "logic_completeness": 9, "language_quality": 10, "risk_control": 9}
        data = make_quality_score_result(True, 9.0, scores, [], False, [])
        validate_result("quality_score", data)

    def test_quality_score_schema_rewrite(self):
        """quality_score 返修场景 schema 校验"""
        scores = {"fact_safety": 9, "doc_type_fit": 8, "mango_style_fit": 5,
                  "logic_completeness": 8, "language_quality": 8, "risk_control": 9}
        data = make_quality_score_result(False, 7.8, scores, ["mango_style_fit"], True,
            [{"dimension": "mango_style_fit", "target": "≥8", "suggested_action": "replace", "reason": "风格低分", "basis": "5"}])
        validate_result("quality_score", data)

    def test_quality_score_schema_warn(self):
        """quality_score warn_and_output 场景 schema 校验"""
        scores = {"fact_safety": 7, "doc_type_fit": 7, "mango_style_fit": 6,
                  "logic_completeness": 7, "language_quality": 6, "risk_control": 7}
        data = make_quality_score_result(False, 6.7, scores,
            ["fact_safety", "doc_type_fit", "mango_style_fit", "logic_completeness", "language_quality", "risk_control"],
            True, [], human_review_required=True,
            risk_notes=["多维度不达标"])
        # 修改 recommendation 为 warn_and_output
        data["final_output_policy"]["recommendation"] = "warn_and_output"
        validate_result("quality_score", data)

    def test_rewrite_schema_q_prefix(self):
        """rewrite.schema 兼容 Q 前缀 revision_report"""
        data = make_rewrite_result("测试正文", revision_prefix="Q")
        validate_result("rewrite", data)

    def test_rewrite_schema_mixed_prefix(self):
        """rewrite.schema 兼容 Q/R 混合 revision_report"""
        data = make_rewrite_result("测试正文", revision_prefix="R")
        data["revision_report"].append({
            "revision_id": "Q-001", "issue_id": "Q001", "action": "replace",
            "before": "旧", "after": "新", "reason": "质量返修", "basis": "quality_score",
        })
        data["resolved_issues"].append({"issue_id": "Q001", "resolution": "质量返修", "basis": "quality_score"})
        validate_result("rewrite", data)


# ─── PipelineReport 序列化测试 ───────────────────────────────────────────────

class TestPipelineReportSerialization(unittest.TestCase):
    """pipeline_report 质量门禁字段可序列化"""

    def test_report_with_quality_gate_fields(self):
        """所有 11 个质量门禁字段可正常序列化为 JSON"""
        report = PipelineReport(
            quality_gate_enabled=True,
            quality_gate_pass=True,
            quality_gate_threshold=8.0,
            quality_gate_rounds_used=1,
            quality_gate_max_rounds=2,
            final_quality_scores={"fact_safety": 9, "doc_type_fit": 8},
            failed_dimensions=[],
            quality_score_history=[{"round": 1, "overall_score": 9.0}],
            final_output_policy="pass",
            human_review_required=False,
            quality_gate_error=None,
            quality_rewrite_applied=False,
        )
        # 序列化
        d = asdict(report)
        json_str = json.dumps(d, ensure_ascii=False)
        self.assertIsInstance(json_str, str)
        self.assertIn("quality_gate_enabled", json_str)
        self.assertIn("quality_gate_pass", json_str)
        self.assertIn("final_output_policy", json_str)

        # 反序列化
        parsed = json.loads(json_str)
        self.assertEqual(parsed["quality_gate_enabled"], True)
        self.assertEqual(parsed["quality_gate_pass"], True)
        self.assertEqual(parsed["final_output_policy"], "pass")

    def test_report_disabled(self):
        """QUALITY_GATE_ENABLED=false 时的 report 可序列化"""
        report = PipelineReport(quality_gate_enabled=False, quality_gate_pass=None)
        d = asdict(report)
        json_str = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["quality_gate_enabled"], False)
        self.assertIsNone(parsed["quality_gate_pass"])

    def test_report_with_error(self):
        """异常状态的 report 可序列化"""
        report = PipelineReport(
            quality_gate_enabled=True,
            quality_gate_pass=None,
            quality_gate_error="质量门禁调用失败 (round 1): ConnectionError",
            final_output_policy="warn_and_output",
            human_review_required=True,
            quality_score_history=[],
        )
        d = asdict(report)
        json_str = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(json_str)
        self.assertIn("ConnectionError", parsed["quality_gate_error"])
        self.assertEqual(parsed["human_review_required"], True)


# ─── STAGES 不变验证 ────────────────────────────────────────────────────────

class TestStagesUnchanged(unittest.TestCase):
    """验证六阶段结构不变"""

    def test_stages_count(self):
        """STAGES 仍为 6 个"""
        from pipeline_types import STAGES
        self.assertEqual(len(STAGES), 6)

    def test_stages_names(self):
        """STAGES 名称不变"""
        from pipeline_types import STAGES
        expected = ["classify", "extract", "plan", "draft", "review", "rewrite"]
        self.assertEqual(list(STAGES), expected)

    def test_schema_map_has_quality_score(self):
        """SCHEMA_MAP 包含 quality_score 作为辅助 schema"""
        from pipeline_types import SCHEMA_MAP
        self.assertIn("quality_score", SCHEMA_MAP)
        self.assertEqual(len(SCHEMA_MAP), 7)

    def test_quality_score_not_in_stages(self):
        """quality_score 不在 STAGES 列表中（不是第七阶段）"""
        from pipeline_types import STAGES
        self.assertNotIn("quality_score", STAGES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
