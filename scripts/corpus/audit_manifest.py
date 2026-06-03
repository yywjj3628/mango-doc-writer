#!/usr/bin/env python3
"""
mango-doc-writer v0.2.0 — Stage A3
Manifest / Metadata Audit Tool

审计 manifest.jsonl + metadata/*.meta.json + cleaned/*.md，
检查一致性、RAG 边界、完整性、重复。

不连接飞书，不写 Base，不入 Qdrant，不改 pipeline，不自动修复。

用法:
  python3 scripts/corpus/audit_manifest.py \
    --manifest /tmp/corpus/manifests/manifest-v0.2.0.jsonl \
    --corpus-root /tmp/corpus \
    --output /tmp/corpus/audits/audit-report.md \
    --format markdown
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter

# ─────────────────────────────────────────────
# 允许的 source 列表
# ─────────────────────────────────────────────

ALLOWED_SOURCES = {
    "电广传媒司情", "湖南广播电视台办公室", "湖南广电党建",
    "清风芒果", "电广传媒917", "湖南广播电视台", "芒果TV",
    "芒果", "unknown",
}

# 目录噪音正则
DIRECTORY_NOISE_RE = re.compile(r'(内容提要|目录\s*[：:]\s*|第[一二三四五六七八九十\d]+[章节期])')
BULLET_NOISE_RE = re.compile(r'(●|■|◆|★|☆|▸|▹|➤|►|•){5,}')

# 日期格式
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# ─────────────────────────────────────────────
# 数据结构
# ─────────────────────────────────────────────

class Issue:
    def __init__(self, doc_id, severity, code, message, field=None):
        self.doc_id = doc_id
        self.severity = severity  # ERROR / WARN / INFO
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self):
        d = {"doc_id": self.doc_id, "severity": self.severity, "code": self.code, "message": self.message}
        if self.field:
            d["field"] = self.field
        return d


def load_manifest(manifest_path):
    """加载 manifest.jsonl，返回 (entries, issues)"""
    entries = []
    issues = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                issues.append(Issue(f"line:{line_num}", "ERROR", "manifest_json_invalid", str(e)))
    return entries, issues


def load_metadata(meta_path):
    """加载单个 .meta.json"""
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_file_hash(filepath):
    """计算文件 SHA-256"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return hashlib.sha256(content.encode("utf-8")).hexdigest(), content
    except Exception:
        return None, None


def audit_entry(entry, corpus_root, min_body_chars, doc_id_counter, dup_key_counter):
    """审计单条 manifest entry，返回 issues 列表"""
    issues = []
    doc_id = entry.get("doc_id", "")

    # ── 必填字段 ──
    for field in ("doc_id", "title", "body_md_path", "meta_json_path", "lark_record_id",
                  "source", "source_type", "clean_status"):
        if not entry.get(field):
            issues.append(Issue(doc_id, "ERROR", f"missing_{field}", f"Manifest field '{field}' is empty"))

    # doc_id 重复
    doc_id_counter[doc_id] += 1
    if doc_id_counter[doc_id] > 1:
        issues.append(Issue(doc_id, "ERROR", "duplicate_doc_id", f"doc_id '{doc_id}' appears more than once"))

    # ── 文件存在性 ──
    body_path = os.path.join(corpus_root, entry.get("body_md_path", ""))
    meta_path = os.path.join(corpus_root, entry.get("meta_json_path", ""))

    if not entry.get("body_md_path") or not os.path.isfile(body_path):
        issues.append(Issue(doc_id, "ERROR", "missing_body_file",
                            f"Body file not found: {entry.get('body_md_path', 'N/A')}"))
    else:
        # 正文内容检查
        content_hash, body_text = compute_file_hash(body_path)
        if body_text is None:
            issues.append(Issue(doc_id, "ERROR", "body_read_error", f"Cannot read {body_path}"))
        else:
            # 去掉 front matter 后的正文
            clean_body = body_text
            if body_text.startswith("---"):
                fm_end = body_text.find("---", 3)
                if fm_end >= 0:
                    clean_body = body_text[fm_end + 3:].strip()

            if not clean_body:
                issues.append(Issue(doc_id, "ERROR", "empty_body", "Body is empty after front matter"))
            else:
                # content_hash 检查
                expected_hash = entry.get("content_hash", "")
                actual_hash = hashlib.sha256(clean_body.encode("utf-8")).hexdigest()
                if expected_hash and expected_hash != actual_hash:
                    issues.append(Issue(doc_id, "ERROR", "content_hash_mismatch",
                                        f"Expected {expected_hash[:16]}... got {actual_hash[:16]}..."))

                # char_count 检查
                expected_chars = entry.get("char_count")
                if expected_chars is not None:
                    actual_chars = len(clean_body)
                    if abs(actual_chars - expected_chars) > 10:
                        issues.append(Issue(doc_id, "WARN", "char_count_mismatch",
                                            f"manifest={expected_chars}, actual={actual_chars}"))

                # 正文过短
                if len(clean_body) < min_body_chars:
                    issues.append(Issue(doc_id, "WARN", "body_too_short",
                                        f"Body length {len(clean_body)} < {min_body_chars}"))

                # 目录噪音
                if DIRECTORY_NOISE_RE.search(clean_body[:500]):
                    issues.append(Issue(doc_id, "WARN", "directory_noise",
                                        "Body starts with table-of-contents pattern"))
                if BULLET_NOISE_RE.search(clean_body[:300]):
                    issues.append(Issue(doc_id, "WARN", "bullet_noise",
                                        "Body contains excessive bullet characters"))

    # metadata 文件存在性
    if not entry.get("meta_json_path") or not os.path.isfile(meta_path):
        issues.append(Issue(doc_id, "ERROR", "missing_meta_file",
                            f"Metadata file not found: {entry.get('meta_json_path', 'N/A')}"))
    else:
        try:
            meta = load_metadata(meta_path)
        except json.JSONDecodeError as e:
            issues.append(Issue(doc_id, "ERROR", "meta_json_invalid", f"Metadata JSON parse error: {e}"))
            return issues

        # doc_id 一致性
        meta_doc_id = meta.get("doc_id", "")
        if meta_doc_id and meta_doc_id != doc_id:
            issues.append(Issue(doc_id, "ERROR", "doc_id_mismatch",
                                f"Manifest doc_id={doc_id}, metadata doc_id={meta_doc_id}"))

        # ── RAG 边界（硬性） ──
        rag_checks = {
            "rag_usage": "style_only",
            "is_fact_safe": False,
            "fact_usage_allowed": False,
            "official_reference_allowed": False,
        }
        for field, expected in rag_checks.items():
            actual = meta.get(field)
            if actual != expected:
                issues.append(Issue(doc_id, "ERROR", f"rag_boundary_{field}",
                                    f"{field}={actual}, expected={expected}", field))

        # ── RAG 边界（软性） ──
        if meta.get("needs_manual_review") and meta.get("audit_status") != "review_required":
            issues.append(Issue(doc_id, "WARN", "review_status_mismatch",
                                "needs_manual_review=true but audit_status != review_required"))

        # ── 时间格式 ──
        pub_date = meta.get("publish_date")
        if not pub_date:
            issues.append(Issue(doc_id, "WARN", "missing_publish_date", "publish_date is empty"))
        elif not DATE_RE.match(str(pub_date)):
            issues.append(Issue(doc_id, "WARN", "invalid_publish_date", f"publish_date format: {pub_date}"))

        # ── clean_status ──
        cs = meta.get("clean_status")
        if not cs or cs == "unknown":
            if "missing_clean_status_bootstrap" in meta.get("audit_warnings", []):
                issues.append(Issue(doc_id, "WARN", "missing_clean_status_bootstrap",
                                    "Record from old table without clean_status"))
            else:
                issues.append(Issue(doc_id, "WARN", "missing_clean_status", "clean_status is empty/unknown"))

        # ── needs_manual_review ──
        if meta.get("needs_manual_review"):
            issues.append(Issue(doc_id, "WARN", "needs_manual_review",
                                f"Record needs manual review: {meta.get('manual_review_reason', 'N/A')}"))

        # ── source 白名单 ──
        source = meta.get("source", "")
        if source and source not in ALLOWED_SOURCES:
            issues.append(Issue(doc_id, "WARN", "source_not_allowed", f"Source '{source}' not in allowed list"))

        # ── duplicate_key 重复 ──
        dup_key = meta.get("duplicate_key", "")
        if dup_key:
            dup_key_counter[dup_key] += 1
            if dup_key_counter[dup_key] > 1:
                issues.append(Issue(doc_id, "WARN", "duplicate_key", f"duplicate_key collision: {dup_key[:80]}"))

        # ── INFO ──
        if meta.get("needs_manual_review"):
            issues.append(Issue(doc_id, "INFO", "review_required_record",
                                "This record requires manual review before RAG ingest"))
        if meta.get("rule_candidate_allowed") and not meta.get("is_fact_safe"):
            issues.append(Issue(doc_id, "INFO", "rule_candidate_only",
                                "Can be used for rule candidate extraction, not as fact source"))

    return issues


def generate_markdown_report(issues, entries, check_counts, rag_summary, review_records,
                             dup_doc_ids, dup_keys, output_path):
    """生成 Markdown 审计报告"""
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARN"]
    infos = [i for i in issues if i.severity == "INFO"]
    passed = len(entries) - len(set(i.doc_id for i in errors))

    lines = []
    lines.append("# Corpus Manifest Audit Report\n")
    lines.append(f"> Generated by mango-doc-writer v0.2.0 A3 audit tool\n")
    lines.append("")

    # Summary
    lines.append("## 1. Audit Summary\n")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Records | {len(entries)} |")
    lines.append(f"| ✅ Passed | {passed} |")
    lines.append(f"| ❌ Errors | {len(errors)} |")
    lines.append(f"| ⚠️ Warnings | {len(warnings)} |")
    lines.append(f"| ℹ️ Info | {len(infos)} |")
    lines.append(f"| **Result** | **{'PASS ✅' if not errors else 'FAIL ❌'}** |")
    lines.append("")

    # Check Results
    lines.append("## 2. Check Results\n")
    lines.append("| Check Code | Count |")
    lines.append("|-----------|-------|")
    for code, count in sorted(check_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {code} | {count} |")
    lines.append("")

    # Errors
    if errors:
        lines.append("## 3. Errors\n")
        lines.append("| doc_id | Code | Message |")
        lines.append("|--------|------|---------|")
        for i in errors[:50]:
            lines.append(f"| `{i.doc_id}` | {i.code} | {i.message[:80]} |")
        if len(errors) > 50:
            lines.append(f"| ... | ... | +{len(errors)-50} more |")
        lines.append("")

    # Warnings
    if warnings:
        lines.append("## 4. Warnings\n")
        lines.append("| doc_id | Code | Message |")
        lines.append("|--------|------|---------|")
        for i in warnings[:100]:
            lines.append(f"| `{i.doc_id}` | {i.code} | {i.message[:80]} |")
        if len(warnings) > 100:
            lines.append(f"| ... | ... | +{len(warnings)-100} more |")
        lines.append("")

    # RAG Boundary
    lines.append("## 5. RAG Boundary Summary\n")
    lines.append(f"| Field | Value | Count |")
    lines.append(f"|-------|-------|-------|")
    for field, count in rag_summary.items():
        lines.append(f"| {field} | {count} |")
    lines.append("")

    # Review Required
    if review_records:
        lines.append("## 6. Review Required Records\n")
        for rec in review_records:
            lines.append(f"- `{rec}`")
        lines.append("")

    # Duplicates
    if dup_doc_ids or dup_keys:
        lines.append("## 7. Duplicate Summary\n")
        if dup_doc_ids:
            lines.append("**Duplicate doc_ids:**")
            for did in dup_doc_ids:
                lines.append(f"- `{did}`")
        if dup_keys:
            lines.append("**Duplicate keys:**")
            for dk in dup_keys:
                lines.append(f"- `{dk[:100]}`")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return len(errors)


def generate_json_report(issues, entries, output_path):
    """生成 JSON 审计报告"""
    report = {
        "total_records": len(entries),
        "error_count": sum(1 for i in issues if i.severity == "ERROR"),
        "warning_count": sum(1 for i in issues if i.severity == "WARN"),
        "info_count": sum(1 for i in issues if i.severity == "INFO"),
        "result": "PASS" if not any(i.severity == "ERROR" for i in issues) else "FAIL",
        "issues": [i.to_dict() for i in issues],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report["error_count"]


def main():
    parser = argparse.ArgumentParser(description="A3: manifest / metadata audit")
    parser.add_argument("--manifest", required=True, help="Path to manifest.jsonl")
    parser.add_argument("--corpus-root", required=True, help="Corpus root directory")
    parser.add_argument("--output", required=True, help="Output report path")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"])
    parser.add_argument("--fail-on-error", action="store_true", help="Exit 1 if any ERROR")
    parser.add_argument("--min-body-chars", type=int, default=80, help="Minimum body length warning threshold")
    args = parser.parse_args()

    manifest_path = os.path.abspath(args.manifest)
    corpus_root = os.path.abspath(args.corpus_root)
    output_path = os.path.abspath(args.output)

    # 加载 manifest
    entries, manifest_issues = load_manifest(manifest_path)
    all_issues = manifest_issues[:]

    doc_id_counter = Counter()
    dup_key_counter = Counter()
    check_counts = Counter()
    rag_summary = Counter()
    review_records = []

    # 审计每条
    for entry in entries:
        issues = audit_entry(entry, corpus_root, args.min_body_chars, doc_id_counter, dup_key_counter)
        all_issues.extend(issues)
        for i in issues:
            check_counts[i.code] += 1

        # RAG 边界统计
        rag_summary["rag_usage=style_only"] += 1  # 只统计有记录的
        rag_summary["is_fact_safe=false"] += 1

        # review_required
        if any(i.code == "needs_manual_review" and i.severity == "WARN" for i in issues):
            review_records.append(entry.get("doc_id", "unknown"))

    # 收集重复
    dup_doc_ids = [did for did, cnt in doc_id_counter.items() if cnt > 1]
    dup_keys = [dk for dk, cnt in dup_key_counter.items() if cnt > 1]

    # RAG 边界实际统计（从 metadata 读取）
    rag_summary = Counter()
    for entry in entries:
        meta_path = os.path.join(corpus_root, entry.get("meta_json_path", ""))
        if os.path.isfile(meta_path):
            try:
                meta = load_metadata(meta_path)
                rag_summary[f"rag_usage={meta.get('rag_usage', 'N/A')}"] += 1
                rag_summary[f"is_fact_safe={meta.get('is_fact_safe', 'N/A')}"] += 1
                rag_summary[f"fact_usage_allowed={meta.get('fact_usage_allowed', 'N/A')}"] += 1
                rag_summary[f"official_reference_allowed={meta.get('official_reference_allowed', 'N/A')}"] += 1
            except Exception:
                pass

    # 生成报告
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    error_count = 0
    if args.format == "json":
        error_count = generate_json_report(all_issues, entries, output_path)
    else:
        error_count = generate_markdown_report(
            all_issues, entries, check_counts, rag_summary, review_records,
            dup_doc_ids, dup_keys, output_path,
        )

    # 控制台摘要
    errors = sum(1 for i in all_issues if i.severity == "ERROR")
    warns = sum(1 for i in all_issues if i.severity == "WARN")
    infos = sum(1 for i in all_issues if i.severity == "INFO")

    print(f"\n{'='*60}")
    print(f"AUDIT RESULT: {'PASS ✅' if errors == 0 else 'FAIL ❌'}")
    print(f"{'='*60}")
    print(f"  Records:  {len(entries)}")
    print(f"  Errors:   {errors}")
    print(f"  Warnings: {warns}")
    print(f"  Info:     {infos}")
    print(f"  Report:   {output_path}")
    print(f"{'='*60}")

    if args.fail_on_error and errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
