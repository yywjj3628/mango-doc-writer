"""
output_formatter.py — 将 pipeline 结果格式化为用户可读输出

策略：
- final_markdown 放最前
- manual_confirmation_fields 简洁展示
- remaining_risks 简洁展示
- pipeline_report 只展示摘要
- 不暴露六阶段 JSON 全量
"""

import json
import os
from typing import Any, Dict, Optional


def format_output(pipeline_result, output_dir: str) -> Dict[str, Any]:
    """将 pipeline 结果格式化为 OpenClaw 用户可读输出"""
    report = pipeline_result.pipeline_report
    rewrite = pipeline_result.partial_results.get("rewrite", {})
    status = report.status

    if status == "failed":
        return _format_failed(report, output_dir)

    # final_markdown 路径
    md_path = os.path.join(output_dir, "final_markdown.md")
    final_md = ""
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            final_md = f.read().strip()

    # manual_confirmation_fields
    mc_fields = rewrite.get("manual_confirmation_fields", [])

    # remaining_risks
    risks = rewrite.get("remaining_risks", [])

    # warnings
    all_warnings = []
    for stage_name in ["classify", "extract", "plan", "draft", "review", "rewrite"]:
        stage_data = pipeline_result.partial_results.get(stage_name, {})
        for w in stage_data.get("warnings", []):
            level = w.get("level", "low")
            if level in ("high", "critical"):
                all_warnings.append(w)

    # sanitizer high-risk
    hr_san = report.sanitizer_high_risk

    # 质量门禁字段
    qg_enabled = report.quality_gate_enabled
    qg_pass = report.quality_gate_pass
    qg_scores = report.final_quality_scores
    qg_failed_dims = report.failed_dimensions
    qg_rounds = report.quality_gate_rounds_used
    qg_max_rounds = report.quality_gate_max_rounds
    qg_output_policy = report.final_output_policy
    qg_rewrite_applied = report.quality_rewrite_applied
    qg_error = report.quality_gate_error
    qg_history = report.quality_score_history
    qg_human_review = report.human_review_required

    output = {
        "status": "success",
        "doc_type": report.doc_type,
        "final_markdown": final_md,
        "manual_confirmation_fields": [
            {
                "field": f.get("field", ""),
                "reason": f.get("reason", ""),
                "impact": f.get("impact", ""),
                "required": f.get("required_before_final", False),
            }
            for f in mc_fields
        ],
        "remaining_risks": [
            {
                "level": r.get("level", "medium") if isinstance(r, dict) else "medium",
                "detail": r.get("detail", str(r)) if isinstance(r, dict) else str(r),
            }
            for r in risks
        ],
        "warnings": all_warnings,
        "output_files": {
            "markdown": md_path,
            "docx": None,  # DOCX 按需生成
            "pipeline_report": os.path.join(output_dir, "pipeline_report.json"),
            "sanitizer_report": os.path.join(output_dir, "sanitizer_report.json") if os.path.exists(
                os.path.join(output_dir, "sanitizer_report.json")) else None,
        },
        "summary": {
            "doc_type": report.doc_type,
            "risk_level": report.risk_level,
            "review_pass": report.review_pass,
            "rewrite_required": report.rewrite_required,
            "rag_status": report.rag_status,
            "style_references_count": report.style_references_count,
            "rag_collection": report.rag_collection,
            "rag_index": report.rag_index,
            "rag_query": report.rag_query,
            "rag_sources": report.rag_sources,
            "default_model": report.default_model,
            "fallback_count": report.fallback_count,
            "high_risk_sanitizer": hr_san,
            "manual_confirmation_count": len(mc_fields),
            "remaining_risk_count": len(risks),
        },
    }

    # 质量门禁摘要
    if qg_enabled and qg_scores is not None:
        output["quality_gate"] = {
            "enabled": True,
            "pass": qg_pass,
            "scores": qg_scores,
            "failed_dimensions": qg_failed_dims,
            "rounds_used": qg_rounds,
            "max_rounds": qg_max_rounds,
            "rewrite_applied": qg_rewrite_applied,
            "output_policy": qg_output_policy,
            "human_review_required": qg_human_review,
            "score_history": qg_history,
        }
    elif qg_enabled and qg_error:
        output["quality_gate"] = {
            "enabled": True,
            "pass": None,
            "error": qg_error,
            "output_policy": qg_output_policy or "warn_and_output",
            "human_review_required": True,
        }
    elif not qg_enabled:
        output["quality_gate"] = {"enabled": False}

    if hr_san:
        output["advisory"] = "⚠️ 本次运行触发了高风险 sanitizer 自动修正，建议人工复核"

    return output


def _format_failed(report, output_dir: str) -> Dict[str, Any]:
    """格式化失败结果"""
    debug_dir = os.path.join(output_dir, "..", "debug")
    debug_files = []
    if os.path.isdir(debug_dir):
        debug_files = sorted(os.listdir(debug_dir))

    return {
        "status": "failed",
        "doc_type": report.doc_type,
        "failed_stage": report.failed_stage,
        "error_type": "pipeline_error",
        "error_message": str(report.error) if report.error else "未知错误",
        "debug_output_path": os.path.join(debug_dir, debug_files[0]) if debug_files else None,
        "suggestion": _get_error_suggestion(report.failed_stage, report.error),
    }


def _get_error_suggestion(failed_stage: str, error: Optional[str]) -> str:
    """根据失败阶段给出建议"""
    if not failed_stage:
        return "未知错误，请检查日志"
    if "API key" in str(error) or "DEEPSEEK_API_KEY" in str(error):
        return "API key 未配置。请在 .env 中设置 DEEPSEEK_API_KEY。"
    if "schema" in str(error).lower() and "validation" in str(error).lower():
        return f"Schema 校验失败（{failed_stage}），模型输出格式异常。系统会自动 fallback 到更强模型重试。"
    if "JSON" in str(error) or "json" in str(error).lower():
        return f"JSON 解析失败（{failed_stage}），模型输出格式异常。系统会自动重试。"
    if "RAG" in str(error).upper() or "style_rag" in str(error).lower():
        return "RAG 服务不可达，draft 阶段将跳过风格参考。不影响核心生成。"
    return f"阶段 {failed_stage} 失败，请查看日志了解详情。"


def format_user_text(output: Dict[str, Any]) -> str:
    """将格式化输出转为用户可读文本（用于 OpenClaw 对话）"""
    if output["status"] == "failed":
        lines = [
            f"❌ 文案生成失败",
            f"",
            f"**失败阶段**: {output.get('failed_stage', '未知')}",
            f"**错误**: {output.get('error_message', '')}",
        ]
        if output.get("suggestion"):
            lines.append(f"")
            lines.append(f"💡 {output['suggestion']}")
        return "\n".join(lines)

    lines = []
    lines.append(output.get("final_markdown", ""))
    lines.append("")

    # 待确认项
    mc = output.get("manual_confirmation_fields", [])
    if mc:
        lines.append("---")
        lines.append("📋 **待确认项**")
        for f in mc:
            req = "【必须确认】" if f.get("required") else ""
            lines.append(f"- {f['field']}: {f['reason']} {req}")

    # 剩余风险
    risks = output.get("remaining_risks", [])
    if risks:
        lines.append("")
        lines.append("⚠️ **剩余风险**")
        for r in risks:
            level_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(r.get("level", "medium"), "🟡")
            lines.append(f"{level_icon} {r['detail']}")

    # 摘要
    summary = output.get("summary", {})
    lines.append("")
    lines.append("---")
    lines.append(f"文种: {summary.get('doc_type')} | 风险: {summary.get('risk_level')} | "
                 f"RAG: {summary.get('rag_status')} | 模型: {summary.get('default_model')}")
    if summary.get("fallback_count", 0) > 0:
        lines.append(f"⚠️ 使用了 {summary['fallback_count']} 次 fallback")

    # 高风险 sanitizer 提示
    if output.get("advisory"):
        lines.append("")
        lines.append(output["advisory"])

    # 质量门禁提示
    qg = output.get("quality_gate", {})
    if qg.get("enabled"):
        lines.append("")
        lines.append("---")
        if qg.get("pass") is True:
            scores = qg.get("scores", {})
            score_str = " | ".join(f"{k[:3]}={v}" for k, v in scores.items())
            lines.append(f"✅ 质量门禁通过 ({score_str})")
            if qg.get("rewrite_applied"):
                lines.append(f"   经过 {qg.get('rounds_used', 0)} 轮质量返修")
        elif qg.get("error"):
            lines.append(f"⚠️ 质量门禁异常: {qg['error']}")
            lines.append(f"   当前稿件已输出，建议人工复核")
        else:
            scores = qg.get("scores", {})
            failed = qg.get("failed_dimensions", [])
            score_str = " | ".join(f"{k[:3]}={v}" for k, v in scores.items())
            lines.append(f"⚠️ 质量门禁未通过 ({score_str})")
            if failed:
                lines.append(f"   低分维度: {', '.join(failed)}")
            if qg.get("rewrite_applied"):
                lines.append(f"   已完成 {qg.get('rounds_used', 0)}/{qg.get('max_rounds', 2)} 轮返修")
            lines.append(f"   当前稿件已输出，建议人工复核低分维度")
        if qg.get("human_review_required"):
            lines.append(f"   🔴 需要人工复核")
    else:
        lines.append("")
        lines.append("ℹ️ 质量门禁未启用")

    return "\n".join(lines)
