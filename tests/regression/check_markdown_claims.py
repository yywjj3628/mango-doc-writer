#!/usr/bin/env python3
"""
check_markdown_claims.py — 扫描 final_markdown 中的无依据表达、领导评价、文种冲突。

用法:
  python tests/regression/check_markdown_claims.py <markdown_path> --case-id <case_id>
  python tests/regression/check_markdown_claims.py tests/reports/002-fake-report-real-request/rewrite_result.json --case-id 002-fake-report-real-request

说明:
  - 如果传入的是 rewrite_result.json，会自动从中提取 final_markdown。
  - 如果传入的是 .md 文件，直接读取。
  - --case-id 用于加载该 case 的特殊规则。
"""

import argparse
import json
import sys
import os
import yaml
from pathlib import Path


def load_watchlist(watchlist_path=None):
    """加载观察词表。"""
    if watchlist_path is None:
        watchlist_path = Path(__file__).parent / "watchlist.yaml"
    with open(watchlist_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_final_markdown(path_str):
    """从 rewrite_result.json 提取 final_markdown，或直接读取 .md 文件。"""
    p = Path(path_str)
    if p.suffix == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("final_markdown", "")
    else:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()


# ── per-case 特殊规则 ──
# doc_type 用于 doc_type_conflicts 条件扫描。

CASE_RULES = {
    "001-news": {
        "doc_type": "新闻稿",
        "forbidden_strings": ["领导出席", "领导高度肯定", "领导充分肯定"],
    },
    "002-fake-report-real-request": {
        "doc_type": "请示",
        "forbidden_strings": ["特此报告"],
        "required_strings": ["请示"],
        "allowed_strings": ["妥否，请批示"],
    },
    "003-report": {
        "doc_type": "报告",
        "forbidden_strings": ["请批准", "请批复", "请予支持", "妥否，请批示"],
    },
    "004-notice": {
        "doc_type": "通知",
        "forbidden_strings": ["取得成效", "取得显著效果"],
    },
    "005-meeting-minutes": {
        "doc_type": "会议纪要",
        "forbidden_strings": [],
    },
    "006-leader-speech": {
        "doc_type": "领导讲话",
        "forbidden_strings": ["张三同志", "公司党委书记"],
    },
    "007-summary": {
        "doc_type": "总结",
        "forbidden_strings": ["取得显著成效", "取得重大突破", "荣获"],
    },
    "008-letter": {
        "doc_type": "函",
        "forbidden_strings": ["妥否，请批示", "请批准", "请批复"],
    },
    "009-rag-pollution": {
        "doc_type": "新闻稿",
        "forbidden_strings": [
            "领导高度肯定",
            "广泛影响",
            "社会反响热烈",
            "重大突破",
        ],
    },
    "010-terminology-risk": {
        "doc_type": "汇报材料",
        "forbidden_strings": [],
    },
}


def scan_watchlist(text, categories, label_prefix):
    """扫描文本，返回命中列表。"""
    hits = []
    for word in categories:
        if word in text:
            hits.append({
                "type": label_prefix,
                "word": word,
                "context": _extract_context(text, word),
            })
    return hits


def _extract_context(text, word, context_len=30):
    """提取命中词前后的上下文。"""
    idx = text.find(word)
    if idx == -1:
        return ""
    start = max(0, idx - context_len)
    end = min(len(text), idx + len(word) + context_len)
    return text[start:end].replace("\n", " ")


def check_case_rules(text, case_id):
    """检查 per-case 特殊规则。"""
    rules = CASE_RULES.get(case_id, {})
    hits = []
    warnings = []

    for word in rules.get("forbidden_strings", []):
        if word in text:
            hits.append({
                "type": "case_forbidden",
                "word": word,
                "context": _extract_context(text, word),
            })

    for word in rules.get("required_strings", []):
        if word not in text:
            warnings.append({
                "type": "case_required_missing",
                "word": word,
                "detail": f"期望在 final_markdown 中出现 '{word}'",
            })

    return hits, warnings


def run_check(text, watchlist, case_id=None):
    """执行所有扫描，返回结果。"""
    all_hits = []

    # 1. 扫描 unsupported_claims
    all_hits.extend(
        scan_watchlist(text, watchlist.get("unsupported_claims", []), "unsupported_claims")
    )

    # 2. 扫描 leadership_claims
    all_hits.extend(
        scan_watchlist(text, watchlist.get("leadership_claims", []), "leadership_claims")
    )

    # 3. per-case 特殊规则
    warnings = []
    if case_id:
        case_hits, case_warnings = check_case_rules(text, case_id)
        all_hits.extend(case_hits)
        warnings.extend(case_warnings)

    # 4. doc_type_conflicts 条件扫描
    # report_forbidden: 仅在文种为"报告"时扫描
    # request_forbidden: 仅在文种为"请示"时扫描
    conflicts = watchlist.get("doc_type_conflicts", {})
    case_doc_type = CASE_RULES.get(case_id, {}).get("doc_type", None)
    for sub_type, words in conflicts.items():
        should_scan = False
        if sub_type == "report_forbidden" and case_doc_type == "报告":
            should_scan = True
        elif sub_type == "request_forbidden" and case_doc_type == "请示":
            should_scan = True
        if should_scan:
            all_hits.extend(
                scan_watchlist(text, words, f"doc_type_conflict:{sub_type}")
            )

    pass_result = len(all_hits) == 0

    return {
        "case_id": case_id or "unknown",
        "pass": pass_result,
        "hits": all_hits,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="扫描 final_markdown 中的无依据表达")
    parser.add_argument("path", help="final_markdown.md 或 rewrite_result.json 路径")
    parser.add_argument("--case-id", default=None, help="Case ID（用于加载特殊规则）")
    parser.add_argument("--watchlist", default=None, help="观察词表路径（默认同目录）")
    args = parser.parse_args()

    text = extract_final_markdown(args.path)
    if not text.strip():
        print(json.dumps({"error": "final_markdown 为空", "path": args.path}, ensure_ascii=False))
        sys.exit(1)

    watchlist = load_watchlist(args.watchlist)
    result = run_check(text, watchlist, args.case_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
