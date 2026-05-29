"""
mango-doc-writer 自动化 pipeline

六阶段串联:classify → extract → plan → draft → review → rewrite
每阶段输出使用 jsonschema.validate 校验。
使用 DeepSeek API 作为模型 Provider。
draft 阶段调用 VPS 上现有 style_rag。
"""

import json
import os
import sys
import time
from typing import Any, Dict, Optional

# 将 pipeline 目录加入 path 以便导入
sys.path.insert(0, os.path.dirname(__file__))

from pipeline_types import (
    STAGES,
    PipelineInput,
    PipelineReport,
    PipelineResult,
    StageResult,
)
from schema_loader import load_schema, validate_result
from model_client import call_llm_json
from rag_client import retrieve_style_references
from schema_prompt import build_schema_guard


# 重新导出供外部使用
__all__ = ["run_pipeline", "save_results"]

# 模型调用器状态
MODEL_RUNNER_CONNECTED = True

# ─── Prompt 渲染 ─────────────────────────────────────────────────────────

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(SKILL_DIR, "prompts")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

STAGE_PROMPTS = {
    "classify": "01-classify.md",
    "extract": "02-extract.md",
    "plan": "03-plan.md",
    "draft": "04-draft.md",
    "review": "05-review.md",
    "rewrite": "06-rewrite.md",
    "quality_score": "07-quality-score.md",
}


def _load_prompt_file(stage: str) -> str:
    prompt_file = os.path.join(PROMPTS_DIR, STAGE_PROMPTS[stage])
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


def _load_reference(filename: str) -> str:
    filepath = os.path.join(REFERENCES_DIR, filename)
    if not os.path.exists(filepath):
        return f"[参考文件 {filename} 未找到]"
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _render_template(template: str, variables: Dict[str, str]) -> str:
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        template = template.replace(placeholder, str(value) if value else "")
    return template


# ─── 构造阶段 Prompt ─────────────────────────────────────────────────────


def _build_stage_prompt(stage: str, payload: Dict[str, Any], rag_info: dict = None) -> str:
    """构造阶段 Prompt(不含强制前后缀,DeepSeek 原生支持 JSON mode)"""
    prompt_template = _load_prompt_file(stage)

    template_vars = {
        "requirement": payload.get("requirement", ""),
        "draft": payload.get("draft", ""),
    }

    if stage == "classify":
        template_vars["specified_doc_type"] = payload.get("specified_doc_type", "")
        template_vars["target_unit"] = payload.get("target_unit", "")
        template_vars["scene"] = payload.get("scene", "")

    elif stage in ("extract", "plan", "draft", "review", "rewrite"):
        for prev_stage, template_key in [
            ("classify", "classify_result"),
            ("extract", "extract_result"),
            ("plan", "plan_result"),
            ("draft", "draft_result"),
            ("review", "review_result"),
        ]:
            result = payload.get(prev_stage)
            if result is not None:
                template_vars[template_key] = json.dumps(result, ensure_ascii=False, indent=2)

    if stage in ("plan", "draft", "review", "rewrite"):
        template_vars["doc_type_rules"] = _load_reference("doc-type-rules.md")
        template_vars["org_title_dictionary"] = _load_reference("org-title-dictionary.yaml")

    if stage in ("draft", "review"):
        template_vars["style_rag_policy"] = _load_reference("style-rag-policy.md")

    if stage == "draft" and rag_info:
        # 注入 RAG 风格参考
        style_refs = rag_info.get("summary", "")
        if rag_info.get("warnings"):
            style_refs += "\n\nRAG 警告：" + ";".join(rag_info["warnings"])
        template_vars["style_references"] = style_refs

    if stage == "quality_score":
        template_vars["quality_rewrite_round"] = str(payload.get("quality_rewrite_round", 0))
        template_vars["max_quality_rewrite_rounds"] = str(payload.get("max_quality_rewrite_rounds", 2))

    return _render_template(prompt_template, template_vars)


# ─── 构造 system prompt ─────────────────────────────────────────────────


def _get_system_prompt(stage: str) -> str:
    """获取阶段 system prompt,含 schema 约束"""
    schema_guard = build_schema_guard(stage)
    base = (
        f"你是芒果系文案生产系统的 {stage} 阶段执行器。"
        f"严格按照 Prompt 指令输出严格 JSON。"
        f"不得输出 Markdown 代码块、解释性文字或任何非 JSON 内容。"
    )
    if schema_guard:
        base += "\n\n" + schema_guard
    return base


# ─── Pipeline 核心 ────────────────────────────────────────────────────────


def _build_stage_payload(
    stage: str,
    input_data: PipelineInput,
    completed: Dict[str, dict],
) -> dict:
    """构造每个阶段的输入 payload"""
    base = {
        "requirement": input_data.requirement,
        "draft": input_data.draft,
    }
    if input_data.specified_doc_type:
        base["specified_doc_type"] = input_data.specified_doc_type
    if input_data.target_unit:
        base["target_unit"] = input_data.target_unit
    if input_data.scene:
        base["scene"] = input_data.scene

    # 逐阶段叠加已完成的结果
    payload = {**base, **completed}
    return payload


def _call_stage_api(stage: str, payload: dict, rag_info: dict = None, use_fallback: bool = False) -> tuple:
    """调用 DeepSeek API 执行单个阶段,返回 (result_dict, model_meta)"""
    system_prompt = _get_system_prompt(stage)
    user_prompt = _build_stage_prompt(stage, payload, rag_info)
    response = call_llm_json(system_prompt, user_prompt, stage, use_fallback=use_fallback)
    return response["result"], response["_model_meta"]


# ─── Sanitizer 带记录 ─────────────────────────────────────────────────────

# High-risk const fields that must always be flagged
HIGH_RISK_CONST_FIELDS = {
    "rewrite_policy.body_rewritten", "rewrite_policy.passed",
    "rewrite_policy.no_body_generation", "rewrite_policy.no_rewrite",
    "rewrite_policy.no_new_facts", "rewrite_policy.no_rag_call",
    "review_policy.no_body_generation", "review_policy.no_rewrite",
    "review_policy.no_new_facts", "review_policy.no_rag_call",
}


def _record_fix(fixes: list, path: str, before, after, fix_type: str, risk: str, reason: str):
    """记录一次 sanitizer 修复动作"""
    fixes.append({
        "path": path,
        "before": before,
        "after": after,
        "fix_type": fix_type,
        "risk": risk,
        "reason": reason,
    })


def _strip_extra_fields(obj: dict, schema: dict, fixes: list, path: str = ""):
    """递归移除 schema 不允许的额外字段"""
    if not isinstance(obj, dict) or not isinstance(schema, dict):
        return
    if schema.get("additionalProperties") is False:
        allowed = set(schema.get("properties", {}).keys())
        for k in list(obj.keys()):
            if k not in allowed:
                before = obj[k]
                del obj[k]
                _record_fix(fixes, f"{path}.{k}", before, "(removed)",
                             "strip_extra_field", "low", "additionalProperties=false")
    for key, val in schema.get("properties", {}).items():
        if key not in obj:
            continue
        if isinstance(val, dict):
            if isinstance(obj[key], dict):
                _strip_extra_fields(obj[key], val, fixes, f"{path}.{key}")
            elif val.get("type") == "array" and isinstance(obj[key], list) and isinstance(val.get("items"), dict):
                for i, item in enumerate(obj[key]):
                    if isinstance(item, dict):
                        _strip_extra_fields(item, val["items"], fixes, f"{path}.{key}[{i}]")


def _fill_missing_required(obj: dict, schema: dict, fixes: list, path: str = ""):
    """递归填充缺失的 required 字段"""
    if not isinstance(obj, dict) or not isinstance(schema, dict):
        return
    required = set(schema.get("required", []))
    props = schema.get("properties", {})
    for key in required:
        if key not in obj:
            prop = props.get(key, {})
            ptype = prop.get("type")
            if ptype == "string":
                obj[key] = ""
                risk, ft = "medium", "fill_missing_string"
            elif ptype == "boolean":
                obj[key] = False
                risk, ft = "medium", "fill_missing_boolean"
            elif ptype == "integer":
                obj[key] = 0
                risk, ft = "medium", "fill_missing_number"
            elif ptype == "number":
                obj[key] = 0.0
                risk, ft = "medium", "fill_missing_number"
            elif ptype == "array":
                obj[key] = []
                risk, ft = "medium", "fill_missing_array"
            elif ptype == "object":
                obj[key] = {}
                risk, ft = "medium", "fill_missing_object"
            elif "type" in prop and isinstance(prop["type"], list):
                obj[key] = "" if "string" in prop["type"] else None
                risk, ft = "medium", "fill_missing"
            else:
                obj[key] = ""
                risk, ft = "medium", "fill_missing"
            _record_fix(fixes, f"{path}.{key}", "(missing)", obj[key], ft, risk,
                         f"required field, type={ptype}")
    for key, val in props.items():
        if key not in obj:
            continue
        if isinstance(val, dict):
            if isinstance(obj[key], dict):
                _fill_missing_required(obj[key], val, fixes, f"{path}.{key}")
            elif val.get("type") == "array" and isinstance(obj[key], list) and isinstance(val.get("items"), dict):
                for i, item in enumerate(obj[key]):
                    if isinstance(item, dict):
                        _fill_missing_required(item, val["items"], fixes, f"{path}.{key}[{i}]")


def _fix_const_fields(obj: dict, schema: dict, fixes: list, path: str = ""):
    """修复 const 约束字段"""
    if not isinstance(obj, dict) or not isinstance(schema, dict):
        return
    props = schema.get("properties", {})
    for key, prop in props.items():
        if "const" in prop and key in obj:
            full_path = f"{path}.{key}"
            if obj[key] != prop["const"]:
                before = obj[key]
                obj[key] = prop["const"]
                risk = "high" if full_path.lstrip(".") in HIGH_RISK_CONST_FIELDS else "medium"
                _record_fix(fixes, full_path, before, prop["const"],
                             "fix_const_field", risk, f"const={prop['const']}")
        if isinstance(prop, dict):
            if isinstance(obj.get(key), dict):
                _fix_const_fields(obj[key], prop, fixes, f"{path}.{key}")
            elif prop.get("type") == "array" and isinstance(obj.get(key), list) and isinstance(prop.get("items"), dict):
                for i, item in enumerate(obj[key]):
                    if isinstance(item, dict):
                        _fix_const_fields(item, prop["items"], fixes, f"{path}.{key}[{i}]")


def _fix_null_strings(obj: dict, schema: dict, fixes: list, path: str = ""):
    """将 null string 字段转为空字符串"""
    if not isinstance(obj, dict) or not isinstance(schema, dict):
        return
    props = schema.get("properties", {})
    for key, val in props.items():
        if key in obj and obj[key] is None:
            ptype = val.get("type")
            if ptype == "string":
                obj[key] = ""
                _record_fix(fixes, f"{path}.{key}", None, "", "null_to_empty_string", "low",
                             "schema requires string")
        if key in obj and isinstance(val, dict):
            if isinstance(obj[key], dict):
                _fix_null_strings(obj[key], val, fixes, f"{path}.{key}")
            elif val.get("type") == "array" and isinstance(obj[key], list) and isinstance(val.get("items"), dict):
                for i, item in enumerate(obj[key]):
                    if isinstance(item, dict):
                        _fix_null_strings(item, val["items"], fixes, f"{path}.{key}[{i}]")


def _fix_enum_values(obj: dict, schema: dict, fixes: list, path: str = ""):
    """修复 enum 字段的非法值(非 allowed 枚举 → "other" 或第一个合法值)"""
    if not isinstance(obj, dict) or not isinstance(schema, dict):
        return
    props = schema.get("properties", {})
    for key, val in props.items():
        if key in obj and "enum" in val and isinstance(obj[key], str):
            if obj[key] not in val["enum"]:
                before = obj[key]
                # 如果有 other 用 other,否则用第一个
                fallback_val = "other" if "other" in val["enum"] else val["enum"][0]
                obj[key] = fallback_val
                _record_fix(fixes, f"{path}.{key}", before, fallback_val,
                             "enum_to_other", "low",
                             f"allowed={val['enum']}")
        if key in obj and isinstance(val, dict):
            if isinstance(obj[key], dict):
                _fix_enum_values(obj[key], val, fixes, f"{path}.{key}")
            elif val.get("type") == "array" and isinstance(obj[key], list) and isinstance(val.get("items"), dict):
                for i, item in enumerate(obj[key]):
                    if isinstance(item, dict):
                        _fix_enum_values(item, val["items"], fixes, f"{path}.{key}[{i}]")


def _sanitize_output(stage: str, result: dict) -> dict:
    """清洗模型输出,返回 (result, fixes_list, has_high_risk)"""
    fixes = []
    has_high_risk = False
    try:
        schema = load_schema(stage)
        _fix_null_strings(result, schema, fixes)
        _fix_enum_values(result, schema, fixes)
        _strip_extra_fields(result, schema, fixes)
        _fill_missing_required(result, schema, fixes)
        _fix_const_fields(result, schema, fixes)
    except Exception as e:
        fixes.append({
            "path": "(schema_load)", "before": "error", "after": "skipped",
            "fix_type": "sanitize_error", "risk": "low", "reason": str(e),
        })
    has_high_risk = any(f["risk"] == "high" for f in fixes)
    return result, fixes, has_high_risk


def _run_single_stage(
    stage: str,
    payload: dict,
    rag_info: dict = None,
    allow_fallback: bool = True,
) -> StageResult:
    """执行单个阶段(调用 + JSON parse + sanitizer + schema 校验 + 可选 fallback)"""
    model_meta = None

    # 1. 调用模型(默认用 flash)
    try:
        raw_output, model_meta = _call_stage_api(stage, payload, rag_info, use_fallback=False)
    except Exception as e:
        return StageResult(
            stage=stage, status="failed",
            error=f"模型调用异常: {type(e).__name__}: {e}",
            validation_passed=False, model_meta=model_meta,
        )

    result = raw_output

    # 2. 清洗输出(记录所有修复)
    result, sanitizer_fixes, sanitizer_high_risk = _sanitize_output(stage, result)

    # 3. Schema 校验
    try:
        validate_result(stage, result)
        validation_passed = True
    except Exception as schema_err:
        # Schema 校验失败 → 尝试 fallback(如果 high-risk sanitizer 或 flash 不稳定)
        if allow_fallback and (sanitizer_high_risk or True):
            try:
                from model_client import trigger_fallback_call
                fallback_response = trigger_fallback_call(
                    _get_system_prompt(stage),
                    _build_stage_prompt(stage, payload, rag_info),
                    stage,
                    fallback_reason=f"schema_validation_error: {schema_err}",
                )
                fallback_result = fallback_response["result"]
                fallback_meta = fallback_response["_model_meta"]
                model_meta = fallback_meta
                result, fb_fixes, fb_hr = _sanitize_output(stage, fallback_result)
                sanitizer_fixes.extend(fb_fixes)
                if fb_hr:
                    sanitizer_high_risk = True
                try:
                    validate_result(stage, result)
                    return StageResult(
                        stage=stage, status="success", result=result,
                        error=None, validation_passed=True,
                        sanitizer_fixes=sanitizer_fixes, sanitizer_high_risk=sanitizer_high_risk,
                        model_meta=model_meta,
                    )
                except Exception as fb_err:
                    return StageResult(
                        stage=stage, status="failed", result=result,
                        error=f"schema_validation_error (fallback也失败): {fb_err}",
                        validation_passed=False,
                        sanitizer_fixes=sanitizer_fixes, sanitizer_high_risk=sanitizer_high_risk,
                        model_meta=model_meta,
                    )
            except Exception as fb_call_err:
                return StageResult(
                    stage=stage, status="failed", result=result,
                    error=str(schema_err), validation_passed=False,
                    sanitizer_fixes=sanitizer_fixes, sanitizer_high_risk=sanitizer_high_risk,
                    model_meta=model_meta,
                )

        return StageResult(
            stage=stage, status="failed", result=result,
            error=str(schema_err), validation_passed=False,
            sanitizer_fixes=sanitizer_fixes, sanitizer_high_risk=sanitizer_high_risk,
            model_meta=model_meta,
        )

    return StageResult(
        stage=stage, status="success", result=result,
        error=None, validation_passed=True,
        sanitizer_fixes=sanitizer_fixes, sanitizer_high_risk=sanitizer_high_risk,
        model_meta=model_meta,
    )


def run_pipeline(input_data: PipelineInput) -> PipelineResult:
    """
    执行完整的六阶段 pipeline(DeepSeek API 版本)。

    流程:
        classify → extract → plan → draft → review → rewrite

    draft 阶段调用 VPS 上 style_rag。
    每阶段输出都经过 jsonschema.validate 校验。
    任一阶段失败时停止并输出错误报告。
    """
    report = PipelineReport()
    completed: Dict[str, dict] = {}
    output_files: list = []
    start_time = time.time()
    rag_info = {"summary": "", "warnings": [], "status": "not_called", "count": 0,
                "collection": None, "index": None, "query": None, "sources": None,
                "collections_used": None, "primary_collection": None, "fallback_collection": None}
    all_sanitizer_fixes: list = []  # 全局 sanitizer 记录
    any_high_risk = False

    # 模型配置记录
    import os as _os
    report.default_model = _os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    report.fallback_model = _os.getenv("DEEPSEEK_FALLBACK_MODEL", "deepseek-v4-pro")
    report.fallback_enabled = _os.getenv("DEEPSEEK_ENABLE_FALLBACK", "true").lower() == "true"

    # 依次执行六阶段
    for stage in STAGES:
        payload = _build_stage_payload(stage, input_data, completed)

        # draft 阶段:调用 RAG 获取风格参考
        stage_rag_info = None
        if stage == "draft":
            classify_result = completed.get("classify", {})
            doc_type = classify_result.get("doc_type", "其他")

            print(f"  🔍 调用 style_rag ({doc_type})...")
            rag_result = retrieve_style_references(
                doc_type=doc_type,
                requirement=input_data.requirement,
                draft=input_data.draft,
                plan_result=completed.get("plan", {}),
            )

            rag_info["status"] = rag_result["rag_status"]
            rag_info["count"] = rag_result["rag_count"]
            rag_info["collection"] = rag_result.get("rag_primary_collection")
            rag_info["index"] = rag_result.get("rag_primary_collection")
            rag_info["query"] = rag_result.get("rag_query")
            rag_info["sources"] = rag_result.get("rag_sources")
            rag_info["collections_used"] = rag_result.get("rag_collections_used", [])
            rag_info["primary_collection"] = rag_result.get("rag_primary_collection")
            rag_info["fallback_collection"] = rag_result.get("rag_fallback_collection")
            if rag_result.get("rag_error"):
                rag_info["warnings"].append(rag_result["rag_error"])

            # 构造 style_references 文本
            refs = rag_result.get("style_references", [])
            if refs:
                snippets = []
                for ref in refs:
                    for phrase in ref.get("reference_phrases", []):
                        snippets.append(f"- {phrase}")
                rag_info["summary"] = (
                    "RAG 风格参考(仅用于表达风格,不得作为事实来源):\n"
                    + "\n".join(snippets)
                )
            else:
                rag_info["summary"] = "[无风格参考]"

            stage_rag_info = rag_info
            print(f"  📊 RAG 状态: {rag_info['status']}, 参考数: {rag_info['count']}")

        # 执行阶段
        stage_result = _run_single_stage(stage, payload, stage_rag_info)

        if stage_result.status == "failed":
            report.status = "failed"
            report.failed_stage = stage

            if "无法解析为 JSON" in (stage_result.error or ""):
                report.error_type = "invalid_json"
            elif "Schema 校验失败" in (stage_result.error or ""):
                report.error_type = "schema_validation_error"
                from pipeline_types import SCHEMA_MAP
                report.schema_path = f"schemas/{SCHEMA_MAP[stage]}"
            else:
                report.error_type = "stage_error"

            report.error_message = stage_result.error
            report.schema_validation_status = {s: (s in completed) for s in STAGES}
            report.rag_status = rag_info["status"]
            report.style_references_count = rag_info["count"]
            report.rag_collection = rag_info.get("collection")
            report.rag_index = rag_info.get("index")
            report.rag_query = rag_info.get("query")
            report.rag_sources = rag_info.get("sources")
            report.rag_collections_used = rag_info.get("collections_used")
            report.rag_primary_collection = rag_info.get("primary_collection")
            report.rag_fallback_collection = rag_info.get("fallback_collection")

            return PipelineResult(
                status="failed",
                pipeline_report=report,
                partial_results=dict(completed),
                failed_stage=stage,
                error=stage_result.error,
            )

        # 成功 → 保存结果 + 记录 sanitizer
        completed[stage] = stage_result.result
        report.schema_validation_status[stage] = True
        output_files.append(f"{stage}_result.json")
        if stage_result.sanitizer_fixes:
            all_sanitizer_fixes.extend([
                {"stage": stage, **fix} for fix in stage_result.sanitizer_fixes
            ])
        if stage_result.sanitizer_high_risk:
            any_high_risk = True
        # 记录模型使用
        if stage_result.model_meta:
            report.stage_model_usage[stage] = {
                "model": stage_result.model_meta.get("model"),
                "fallback_used": stage_result.model_meta.get("fallback_used", False),
                "fallback_reason": stage_result.model_meta.get("fallback_reason"),
            }
            if stage_result.model_meta.get("fallback_used"):
                report.fallback_count += 1

    # ─── 全部成功 → 提取报告字段 ───────────────────────────────────

    report.status = "success"

    classify_result = completed.get("classify", {})
    review_result = completed.get("review", {})
    rewrite_result = completed.get("rewrite", {})

    report.doc_type = classify_result.get("doc_type")
    report.risk_level = classify_result.get("risk_level") or rewrite_result.get("risk_level")
    report.review_pass = review_result.get("pass")
    report.rewrite_required = review_result.get("rewrite_required")

    extract_result = completed.get("extract", {})
    plan_result = completed.get("plan", {})

    for stage_data in [classify_result, extract_result, plan_result, rewrite_result]:
        mc = stage_data.get("manual_confirmation_fields", [])
        report.manual_confirmation_count += len(mc) if isinstance(mc, list) else 0

    risks = rewrite_result.get("remaining_risks", [])
    report.remaining_risk_count = len(risks) if isinstance(risks, list) else 0

    report.output_files = output_files
    report.rag_status = rag_info["status"]
    report.style_references_count = rag_info["count"]
    report.rag_collection = rag_info.get("collection")
    report.rag_index = rag_info.get("index")
    report.rag_query = rag_info.get("query")
    report.rag_sources = rag_info.get("sources")
    report.rag_collections_used = rag_info.get("collections_used")
    report.rag_primary_collection = rag_info.get("primary_collection")
    report.rag_fallback_collection = rag_info.get("fallback_collection")
    report.sanitizer_high_risk = any_high_risk

    # 从 rewrite_result 提取最终 Markdown
    final_markdown = rewrite_result.get("final_markdown", "")

    # ─── 质量门禁（后置评估，不改变六阶段结构） ───────────────────
    _os = os
    qg_enabled = _os.getenv("QUALITY_GATE_ENABLED", "true").lower() == "true"
    qg_threshold = float(_os.getenv("QUALITY_GATE_THRESHOLD", "8"))
    qg_max_rounds = int(_os.getenv("QUALITY_GATE_MAX_ROUNDS", "2"))

    report.quality_gate_enabled = qg_enabled
    report.quality_gate_threshold = qg_threshold
    report.quality_gate_max_rounds = qg_max_rounds

    if qg_enabled:
        print(f"\n  🏁 质量门禁 (threshold={qg_threshold}, max_rounds={qg_max_rounds})...")

        qg_round = 0
        quality_history = []
        quality_rewrite_applied = False

        while True:
            qg_round += 1
            print(f"  📊 质量评分轮次 {qg_round}/{qg_max_rounds}...")

            # 构造 quality gate payload
            qg_payload = {
                **_build_stage_payload("quality_score", input_data, completed),
                "quality_rewrite_round": qg_round - 1,
                "max_quality_rewrite_rounds": qg_max_rounds,
            }

            # 调用 quality gate（复用现有机制：call_llm_json + sanitizer + schema validation）
            try:
                qg_stage_result = _run_single_stage("quality_score", qg_payload)
            except Exception as qg_err:
                # quality gate 调用失败：保留 final_markdown，标记错误
                report.quality_gate_error = f"质量门禁调用失败 (round {qg_round}): {type(qg_err).__name__}: {qg_err}"
                report.quality_gate_pass = None
                report.final_output_policy = "warn_and_output"
                report.human_review_required = True
                report.quality_score_history = quality_history
                print(f"  ❌ 质量门禁调用失败: {qg_err}")
                break

            if qg_stage_result.status == "failed":
                # quality gate 校验失败：保留 final_markdown，记录错误
                report.quality_gate_error = f"质量门禁校验失败 (round {qg_round}): {qg_stage_result.error}"
                report.quality_gate_pass = None
                report.final_output_policy = "warn_and_output"
                report.human_review_required = True
                report.quality_score_history = quality_history
                print(f"  ❌ 质量门禁失败: {qg_stage_result.error}")
                break

            # quality gate 成功
            qg_result = qg_stage_result.result

            # 记录本轮评分历史
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

            print(f"     overall={qg_result.get('overall_score', '?')}  pass={qg_result.get('overall_pass')}  "
                  f"failed={qg_result.get('failed_dimensions', [])}")

            # 判断是否需要返修
            if qg_result.get("overall_pass", False):
                # 质量达标
                report.quality_gate_pass = True
                report.final_quality_scores = qg_result.get("scores")
                report.failed_dimensions = []
                report.final_output_policy = "pass"
                report.human_review_required = qg_result.get("human_review_required", False)
                print(f"  ✅ 质量门禁通过")
                break

            # 不达标
            if qg_round >= qg_max_rounds:
                # 达到最大返修轮次，不硬失败
                report.quality_gate_pass = False
                report.final_quality_scores = qg_result.get("scores")
                report.failed_dimensions = qg_result.get("failed_dimensions", [])
                report.final_output_policy = "warn_and_output"
                report.human_review_required = True
                report.quality_score_history = quality_history
                print(f"  ⚠️ 达到最大返修轮次 ({qg_max_rounds})，标记 warn_and_output")
                break

            # 需要返修 → 回到 rewrite（不能回到 draft）
            qg_instructions = qg_result.get("quality_rewrite_instructions", [])
            if not qg_instructions:
                # 无返修指令，按 warn 处理
                report.quality_gate_pass = False
                report.final_quality_scores = qg_result.get("scores")
                report.failed_dimensions = qg_result.get("failed_dimensions", [])
                report.final_output_policy = "warn_and_output"
                report.human_review_required = True
                report.quality_score_history = quality_history
                print(f"  ⚠️ 质量不达标但无返修指令，warn_and_output")
                break

            print(f"  🔄 质量返修 round {qg_round}，回到 rewrite...")

            # 构造返修 rewrite payload
            rewrite_payload = {
                **_build_stage_payload("rewrite", input_data, completed),
                "quality_rewrite_instructions": json.dumps(qg_instructions, ensure_ascii=False, indent=2),
            }

            # 保留上一版 final_markdown（安全网）
            prev_final_markdown = final_markdown

            # 执行 rewrite 返修
            rewrite_result = _run_single_stage("rewrite", rewrite_payload)

            if rewrite_result.status == "failed":
                # rewrite 返修失败，保留上一版
                final_markdown = prev_final_markdown
                report.quality_gate_error = f"质量返修 rewrite 失败 (round {qg_round}): {rewrite_result.error}"
                report.quality_gate_pass = False
                report.final_output_policy = "warn_and_output"
                report.human_review_required = True
                report.quality_score_history = quality_history
                print(f"  ❌ 返修 rewrite 失败: {rewrite_result.error}，保留上一版")
                break

            # 返修成功
            quality_rewrite_applied = True
            completed["rewrite"] = rewrite_result.result
            rewrite_result = rewrite_result.result
            final_markdown = rewrite_result.get("final_markdown", prev_final_markdown)
            output_files.append(f"quality_rewrite_round_{qg_round}_result.json")

            if rewrite_result.sanitizer_fixes:
                all_sanitizer_fixes.extend([
                    {"stage": f"quality_rewrite_round_{qg_round}", **fix}
                    for fix in rewrite_result.sanitizer_fixes
                ])
            if rewrite_result.model_meta:
                report.stage_model_usage[f"quality_rewrite_round_{qg_round}"] = {
                    "model": rewrite_result.model_meta.get("model"),
                    "fallback_used": rewrite_result.model_meta.get("fallback_used", False),
                    "fallback_reason": "quality_gate_rewrite",
                }

            print(f"     返修完成，继续下一轮质量评分...")

        # 循环结束，记录最终状态
        report.quality_gate_rounds_used = qg_round
        report.quality_score_history = quality_history
        report.quality_rewrite_applied = quality_rewrite_applied

    else:
        # QUALITY_GATE_ENABLED=false，完全回到 v0.1.2 旧流程
        print("\n  ℹ️ 质量门禁已禁用 (QUALITY_GATE_ENABLED=false)")
        report.quality_gate_enabled = False
        report.quality_gate_pass = None

    elapsed = time.time() - start_time
    print(f"\n✅ Pipeline 完成 ({elapsed:.1f}s)")

    return PipelineResult(
        status="success",
        final_markdown=final_markdown,
        pipeline_report=report,
        partial_results=dict(completed),
        sanitizer_fixes=all_sanitizer_fixes,
    )


# ─── 结果保存 ────────────────────────────────────────────────────────────


def save_results(
    output_dir: str,
    pipeline_result: PipelineResult,
) -> list:
    """将 pipeline 结果保存到指定目录。"""
    os.makedirs(output_dir, exist_ok=True)
    saved_files = []

    stage_keys = ["classify_result", "extract_result", "plan_result",
                  "draft_result", "review_result", "rewrite_result"]

    for stage, stage_name in zip(
        ["classify", "extract", "plan", "draft", "review", "rewrite"],
        stage_keys,
    ):
        result_data = pipeline_result.partial_results.get(stage)
        if result_data is not None:
            filepath = os.path.join(output_dir, f"{stage}_result.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            saved_files.append(filepath)

    if pipeline_result.pipeline_report:
        report_dict = {
            "status": pipeline_result.pipeline_report.status,
            "doc_type": pipeline_result.pipeline_report.doc_type,
            "risk_level": pipeline_result.pipeline_report.risk_level,
            "review_pass": pipeline_result.pipeline_report.review_pass,
            "rewrite_required": pipeline_result.pipeline_report.rewrite_required,
            "manual_confirmation_count": pipeline_result.pipeline_report.manual_confirmation_count,
            "remaining_risk_count": pipeline_result.pipeline_report.remaining_risk_count,
            "schema_validation_status": pipeline_result.pipeline_report.schema_validation_status,
            "rag_status": pipeline_result.pipeline_report.rag_status,
            "style_references_count": pipeline_result.pipeline_report.style_references_count,
            "rag_collection": pipeline_result.pipeline_report.rag_collection,
            "rag_index": pipeline_result.pipeline_report.rag_index,
            "rag_query": pipeline_result.pipeline_report.rag_query,
            "rag_sources": pipeline_result.pipeline_report.rag_sources,
            "rag_collections_used": pipeline_result.pipeline_report.rag_collections_used,
            "rag_primary_collection": pipeline_result.pipeline_report.rag_primary_collection,
            "rag_fallback_collection": pipeline_result.pipeline_report.rag_fallback_collection,
            "failed_stage": pipeline_result.pipeline_report.failed_stage,
            "error_type": pipeline_result.pipeline_report.error_type,
            "error_message": pipeline_result.pipeline_report.error_message,
            "schema_path": pipeline_result.pipeline_report.schema_path,
            "sanitizer_high_risk": pipeline_result.pipeline_report.sanitizer_high_risk,
            "model_provider": "deepseek",
            "default_model": pipeline_result.pipeline_report.default_model,
            "fallback_model": pipeline_result.pipeline_report.fallback_model,
            "fallback_enabled": pipeline_result.pipeline_report.fallback_enabled,
            "stage_model_usage": pipeline_result.pipeline_report.stage_model_usage,
            "fallback_count": pipeline_result.pipeline_report.fallback_count,
            "output_files": pipeline_result.pipeline_report.output_files,
            # 质量门禁字段
            "quality_gate_enabled": pipeline_result.pipeline_report.quality_gate_enabled,
            "quality_gate_pass": pipeline_result.pipeline_report.quality_gate_pass,
            "quality_gate_threshold": pipeline_result.pipeline_report.quality_gate_threshold,
            "quality_gate_rounds_used": pipeline_result.pipeline_report.quality_gate_rounds_used,
            "quality_gate_max_rounds": pipeline_result.pipeline_report.quality_gate_max_rounds,
            "final_quality_scores": pipeline_result.pipeline_report.final_quality_scores,
            "failed_dimensions": pipeline_result.pipeline_report.failed_dimensions,
            "quality_score_history": pipeline_result.pipeline_report.quality_score_history,
            "final_output_policy": pipeline_result.pipeline_report.final_output_policy,
            "human_review_required": pipeline_result.pipeline_report.human_review_required,
            "quality_gate_error": pipeline_result.pipeline_report.quality_gate_error,
            "quality_rewrite_applied": pipeline_result.pipeline_report.quality_rewrite_applied,
        }
        filepath = os.path.join(output_dir, "pipeline_report.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        saved_files.append(filepath)

    if pipeline_result.final_markdown:
        filepath = os.path.join(output_dir, "final_markdown.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(pipeline_result.final_markdown)
        saved_files.append(filepath)

    # sanitizer_report
    if pipeline_result.sanitizer_fixes:
        filepath = os.path.join(output_dir, "sanitizer_report.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(pipeline_result.sanitizer_fixes, f, ensure_ascii=False, indent=2)
        saved_files.append(filepath)

    return saved_files
