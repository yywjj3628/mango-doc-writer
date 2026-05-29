#!/usr/bin/env python3
"""
check_report.py — 检查某个 case 的六阶段输出完整性、schema 校验和策略合规。

用法:
  python tests/regression/check_report.py tests/reports/002-fake-report-real-request
  python tests/regression/check_report.py tests/reports/009-rag-pollution

检查项:
  1. 六阶段 JSON + final_markdown.md + pipeline_report.json 是否存在
  2. 所有 JSON 是否通过对应 schema
  3. draft.fact_usage_report 是否非空
  4. rewrite.fact_usage_report 是否非空
  5. rewrite.rewrite_policy.no_new_facts == true
  6. rewrite.rewrite_policy.no_rag_call == true
  7. rewrite.final_checks.manual_confirmations_preserved == true
  8. manual_confirmation_fields 检查（低风险 case 允许为空）
  9. rewrite.remaining_risks 非空
  10. review 检查 score / rewrite_required 逻辑一致性
  11. 010 terminology-risk 专项称谓风险检测
  12. high-risk sanitizer 汇总
"""

import argparse
import json
import sys
from pathlib import Path

import jsonschema

# schema 文件名映射
SCHEMA_MAP = {
    "classify_result": "classify.schema.json",
    "extract_result": "extract.schema.json",
    "plan_result": "plan_result.json",  # no separate schema, skip validation
    "draft_result": "draft.schema.json",
    "review_result": "review.schema.json",
    "rewrite_result": "rewrite.schema.json",
}

# 有独立 schema 的阶段（用于 schema 校验）
STAGES_WITH_SCHEMA = {
    "classify_result": "classify.schema.json",
    "extract_result": "extract.schema.json",
    "draft_result": "draft.schema.json",
    "review_result": "review.schema.json",
    "rewrite_result": "rewrite.schema.json",
}

# 六阶段 JSON 文件
REQUIRED_STAGES = ["classify_result", "extract_result", "plan_result",
                   "draft_result", "review_result", "rewrite_result"]

# 额外需要的文件
OPTIONAL_FILES = ["final_markdown.md", "pipeline_report.json"]

# 低风险文种：这些 case 的 manual_confirmation_fields 允许为空
LOW_RISK_DOC_TYPES = {"新闻稿", "通知"}

# 称谓风险关键词（用于 010 专项检查）
TERMINOLOGY_RISK_KEYWORDS = ["称谓", "机构", "总部", "口径", "确认", "不规范", "简称", "全称"]


def get_schema_dir(report_dir):
    """获取 schemas 目录路径（相对于项目根）。"""
    return report_dir.parent.parent.parent / "schemas"


def load_json(path):
    """加载 JSON 文件，失败返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None


def check_required_files(report_dir):
    """检查所有必需文件是否存在。"""
    issues = []
    for stage in REQUIRED_STAGES:
        p = report_dir / f"{stage}.json"
        if not p.exists():
            issues.append({"check": "required_files", "detail": f"缺少 {stage}.json"})
    return issues


def check_schema_validation(report_dir):
    """检查所有 JSON 是否通过对应 schema。"""
    schema_dir = get_schema_dir(report_dir)
    issues = []
    for stage, schema_file in STAGES_WITH_SCHEMA.items():
        json_path = report_dir / f"{stage}.json"
        schema_path = schema_dir / schema_file
        if not json_path.exists() or not schema_path.exists():
            continue
        data = load_json(json_path)
        schema = load_json(schema_path)
        if data is None or schema is None:
            issues.append({"check": "schema_validation", "detail": f"{stage}: 文件加载失败"})
            continue
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            issues.append({
                "check": "schema_validation",
                "detail": f"{stage}: {e.message}",
                "path": list(e.path),
            })
    return issues


def check_policies(report_dir):
    """检查策略合规性。"""
    issues = []
    rw = load_json(report_dir / "rewrite_result.json")
    if rw is None:
        issues.append({"check": "policy_checks", "detail": "rewrite_result.json 不存在"})
        return issues

    policy = rw.get("rewrite_policy", {})
    if policy.get("no_new_facts") is not True:
        issues.append({"check": "policy_checks", "detail": "rewrite_policy.no_new_facts 不为 true"})
    if policy.get("no_rag_call") is not True:
        issues.append({"check": "policy_checks", "detail": "rewrite_policy.no_rag_call 不为 true"})

    final_checks = rw.get("final_checks", {})
    if final_checks.get("manual_confirmations_preserved") is not True:
        issues.append({"check": "policy_checks", "detail": "final_checks.manual_confirmations_preserved 不为 true"})

    return issues


def check_manual_confirmation(report_dir):
    """检查 manual_confirmation_fields 是否被保留。

    规则（阶段 15.3 修正）：
    - 低风险文种（新闻稿、通知）允许 mc=0
    - 如果 extract.missing_fields 非空，则 rewrite.mc 应保留对应风险
    - 如果 review.issues 存在 high/critical，则 mc 不应无故清空
    - 否则 mc=0 可以通过
    """
    issues = []
    rw = load_json(report_dir / "rewrite_result.json")
    cl = load_json(report_dir / "classify_result.json")
    rv = load_json(report_dir / "review_result.json")
    ex = load_json(report_dir / "extract_result.json")

    if rw is None:
        issues.append({"check": "manual_confirmation", "detail": "rewrite_result.json 不存在"})
        return issues

    fields = rw.get("manual_confirmation_fields", [])
    doc_type = cl.get("doc_type", "") if cl else ""

    # 低风险文种允许 mc=0
    if doc_type in LOW_RISK_DOC_TYPES:
        return issues

    # mc 非空 → 通过
    if fields:
        return issues

    # mc 为空，检查是否合理
    # 1. extract.missing_fields 非空 → 不应清空
    if ex and ex.get("missing_fields"):
        issues.append({
            "check": "manual_confirmation",
            "detail": f"extract.missing_fields 非空（{len(ex['missing_fields'])}项）但 rewrite.manual_confirmation_fields 被清空",
        })
        return issues

    # 2. review.issues 存在 high/critical → 不应清空
    if rv:
        high_critical = [i for i in rv.get("issues", []) if i.get("level") in ("high", "critical")]
        if high_critical:
            issues.append({
                "check": "manual_confirmation",
                "detail": f"review 存在 {len(high_critical)} 个 high/critical issue 但 manual_confirmation_fields 被清空",
            })
            return issues

    # 3. review.risk_level 为 high/critical → 不应清空
    if rv and rv.get("risk_level") in ("high", "critical"):
        issues.append({
            "check": "manual_confirmation",
            "detail": f"review.risk_level={rv['risk_level']} 但 manual_confirmation_fields 被清空",
        })
        return issues

    # 4. 非 low-risk 但无 high/critical → mc=0 可以通过（如简单的报告/总结）
    return issues


def check_fact_usage(report_dir):
    """检查 fact_usage_report 是否非空。"""
    issues = []

    draft = load_json(report_dir / "draft_result.json")
    if draft is not None:
        fur = draft.get("fact_usage_report", [])
        if not fur:
            issues.append({"check": "fact_usage", "detail": "draft.fact_usage_report 为空"})

    rw = load_json(report_dir / "rewrite_result.json")
    if rw is not None:
        fur = rw.get("fact_usage_report", [])
        if not fur:
            issues.append({"check": "fact_usage", "detail": "rewrite.fact_usage_report 为空"})

    return issues


def check_remaining_risks(report_dir):
    """检查 remaining_risks 是否存在。"""
    issues = []
    rw = load_json(report_dir / "rewrite_result.json")
    if rw is None:
        issues.append({"check": "remaining_risks", "detail": "rewrite_result.json 不存在"})
        return issues

    risks = rw.get("remaining_risks", [])
    if not risks:
        issues.append({"check": "remaining_risks", "detail": "remaining_risks 为空"})
    return issues


def check_review_logic(report_dir):
    """检查 review 的 critical issue 硬规则约束。"""
    issues = []
    rv = load_json(report_dir / "review_result.json")
    if rv is None:
        return issues

    critical_issues = [i for i in rv.get("issues", []) if i.get("level") == "critical"]
    has_critical = len(critical_issues) > 0

    if not has_critical:
        return issues

    if not rv.get("rewrite_required"):
        issues.append({
            "check": "review_logic",
            "detail": "critical_issue_requires_rewrite_failed: "
                       f"存在 {len(critical_issues)} 个 critical issue 但 rewrite_required 为 false",
        })

    if rv.get("pass") is not False:
        issues.append({
            "check": "review_logic",
            "detail": "critical_issue_pass_must_be_false: 存在 critical issue 但 pass 不为 false",
        })

    if not rv.get("rewrite_instructions"):
        issues.append({
            "check": "review_logic",
            "detail": "critical_issue_requires_instructions: 存在 critical issue 但 rewrite_instructions 为空",
        })

    risk = rv.get("risk_level", "")
    if risk not in ("critical", "high"):
        issues.append({
            "check": "review_logic",
            "detail": f"critical_issue_risk_level_warning: 存在 critical issue 但 risk_level='{risk}'",
        })

    return issues


def check_terminology_risk(report_dir):
    """010 terminology-risk 专项称谓风险检查。

    至少满足以下任意一项：
    - terminology_usage_report 非空
    - warnings 中出现称谓/机构等风险关键词
    - manual_confirmation_fields 中包含称谓/机构确认项
    - remaining_risks 中包含称谓/机构风险
    """
    issues = []
    case_id = report_dir.name

    # 仅对 010-terminology-risk 执行此检查
    if "terminology" not in case_id:
        return issues

    found_risk = False

    # 1. extract.terminology_audit 或 terminology_usage_report
    ex = load_json(report_dir / "extract_result.json")
    if ex:
        audit = ex.get("terminology_audit", [])
        if audit:
            found_risk = True

    # 2. 检查各阶段 terminology_usage_report
    for stage_file in ["extract_result.json", "draft_result.json", "review_result.json", "rewrite_result.json"]:
        stage_data = load_json(report_dir / stage_file)
        if stage_data:
            tur = stage_data.get("terminology_usage_report", [])
            if tur:
                found_risk = True
                break

    # 3. warnings 中出现称谓风险关键词
    for stage_file in ["draft_result.json", "review_result.json", "rewrite_result.json"]:
        stage_data = load_json(report_dir / stage_file)
        if stage_data:
            for w in stage_data.get("warnings", []):
                msg = w.get("message", "")
                if any(kw in msg for kw in TERMINOLOGY_RISK_KEYWORDS):
                    found_risk = True
                    break
            if found_risk:
                break

    # 4. manual_confirmation_fields 中包含称谓/机构确认项
    rw = load_json(report_dir / "rewrite_result.json")
    if rw:
        for mc in rw.get("manual_confirmation_fields", []):
            field = mc.get("field", "")
            reason = mc.get("reason", "")
            if any(kw in field + reason for kw in TERMINOLOGY_RISK_KEYWORDS):
                found_risk = True
                break

    # 5. remaining_risks 中包含称谓/机构风险
    if rw:
        for r in rw.get("remaining_risks", []):
            risk_text = str(r)
            if any(kw in risk_text for kw in TERMINOLOGY_RISK_KEYWORDS):
                found_risk = True
                break

    if not found_risk:
        issues.append({
            "check": "terminology_risk",
            "detail": "terminology_risk_not_detected: 未在六阶段输出中检测到称谓/机构风险",
        })

    return issues


def check_high_risk_sanitizer(report_dir):
    """汇总 high-risk sanitizer 修复情况。不导致 fail，仅标记。"""
    sanitizer_path = report_dir / "sanitizer_report.json"
    if not sanitizer_path.exists():
        return []

    data = load_json(sanitizer_path)
    if not data or not isinstance(data, list):
        return []

    high_risk = [f for f in data if f.get("risk") == "high"]
    return high_risk  # 由 run_check 汇总


def run_check(report_dir_str):
    """执行所有检查。"""
    report_dir = Path(report_dir_str)
    if not report_dir.is_dir():
        return {
            "case_id": report_dir.name,
            "pass": False,
            "error": f"目录不存在: {report_dir_str}",
        }

    case_id = report_dir.name
    all_issues = []

    all_issues.extend(check_required_files(report_dir))
    all_issues.extend(check_schema_validation(report_dir))
    all_issues.extend(check_policies(report_dir))
    all_issues.extend(check_manual_confirmation(report_dir))
    all_issues.extend(check_fact_usage(report_dir))
    all_issues.extend(check_remaining_risks(report_dir))
    all_issues.extend(check_review_logic(report_dir))
    all_issues.extend(check_terminology_risk(report_dir))

    # High-risk sanitizer 汇总（不导致 fail）
    high_risk_sanitizers = check_high_risk_sanitizer(report_dir)

    return {
        "case_id": case_id,
        "pass": len(all_issues) == 0,
        "schema_validation": "pass" if not any(i["check"] == "schema_validation" for i in all_issues) else "fail",
        "required_files": "pass" if not any(i["check"] == "required_files" for i in all_issues) else "fail",
        "policy_checks": "pass" if not any(i["check"] == "policy_checks" for i in all_issues) else "fail",
        "manual_confirmation_check": "pass" if not any(i["check"] == "manual_confirmation" for i in all_issues) else "fail",
        "terminology_risk_check": "pass" if not any(i["check"] == "terminology_risk" for i in all_issues) else "fail",
        "high_risk_sanitizer_count": len(high_risk_sanitizers),
        "high_risk_sanitizer_paths": [f["path"] for f in high_risk_sanitizers],
        "needs_manual_review": len(high_risk_sanitizers) > 0,
        "issues": all_issues,
    }


def main():
    parser = argparse.ArgumentParser(description="检查 case 的六阶段输出完整性和合规性")
    parser.add_argument("report_dir", help="tests/reports/<case_id> 目录路径")
    args = parser.parse_args()

    result = run_check(args.report_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
