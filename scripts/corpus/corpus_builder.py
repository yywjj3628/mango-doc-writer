#!/usr/bin/env python3
"""
mango-doc-writer v0.2.0 — 共享 corpus builder 模块。
被 build_corpus_from_base_records.py 和 sync_from_lark_base.py 共同使用。

不连接飞书，不入 Qdrant，不改 pipeline。
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

TZ_CN = timezone(timedelta(hours=8))
SCHEMA_VERSION = "v0.2.0"
CORPUS_COLLECTION = "mango_style_docs"
MANIFEST_FILENAME = "manifest-v0.2.0.jsonl"

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def ts_to_date(val):
    """各种日期格式 → YYYY-MM-DD"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val / 1000, tz=TZ_CN).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            return None
    if isinstance(val, str):
        # lark-cli datetime 格式: "2026-05-19 00:00:00"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(val.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return val.strip()[:10] if len(val.strip()) >= 10 else None
    return None


def ts_to_iso(val):
    """各种日期格式 → ISO 8601"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val / 1000, tz=TZ_CN).isoformat()
        except (ValueError, TypeError, OSError):
            return None
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(val.strip(), fmt).replace(tzinfo=TZ_CN)
                return dt.isoformat()
            except ValueError:
                continue
    return None


def compute_content_hash(body_text):
    return hashlib.sha256(body_text.encode("utf-8")).hexdigest()


def compute_doc_id(source_type, publish_date, title, record_id):
    date_part = publish_date or "unknown"
    raw = f"{source_type}|{title}|{date_part}|{record_id}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    return f"{source_type}_{date_part}_{h}"


def safe_filename(doc_id):
    return re.sub(r'[^\w\-.]', '_', doc_id)


def compute_duplicate_key(source, title, publish_date):
    return f"{source}|{title}|{publish_date or 'unknown'}"


def extract_text_field(field):
    if field is None:
        return ""
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        return "".join(part.get("text", "") for part in field if isinstance(part, dict))
    return str(field)


def extract_first_from_list(field):
    """来源等 select 字段可能是 list 如 ['电广传媒司情']"""
    if field is None:
        return ""
    if isinstance(field, list):
        return field[0] if field else ""
    return str(field)


def infer_source_type(source, existing_type):
    if existing_type and existing_type not in (None, ""):
        return existing_type
    s = source or ""
    if "司情" in s:
        return "weekly_siqing"
    if "芒果日志" in s:
        return "mango_rizhi"
    if "飞书" in s:
        return "feishu_doc"
    return "manual"


# ─────────────────────────────────────────────
# metadata 构建
# ─────────────────────────────────────────────

def build_metadata(record, base_token, table_id, view_id, bootstrap_mode):
    """将 Base-like record → 标准 metadata dict"""
    fields = record.get("fields", {})
    record_id = record.get("record_id", "")

    title = extract_text_field(fields.get("标题")).strip()
    source = extract_first_from_list(fields.get("来源")).strip()
    body = extract_text_field(fields.get("正文")).strip()
    summary = extract_text_field(fields.get("概述")).strip()
    publish_date = ts_to_date(fields.get("时间"))
    issue_date = ts_to_date(fields.get("issue_date"))
    extracted_at = ts_to_iso(fields.get("cleaned_at") or fields.get("时间"))
    sync_ts = datetime.now(TZ_CN).isoformat()

    clean_status_raw = fields.get("clean_status")
    clean_status = extract_first_from_list(clean_status_raw).strip() or None
    split_status_raw = fields.get("split_status")
    split_status = extract_first_from_list(split_status_raw).strip() or None
    needs_manual_review = bool(fields.get("needs_manual_review", False))
    manual_review_reason = extract_text_field(fields.get("manual_review_reason")).strip()
    source_type_raw = fields.get("source_type")
    source_type_val = extract_first_from_list(source_type_raw).strip() or None
    issue_no = fields.get("issue_no")
    total_issue_no = fields.get("total_issue_no")
    tags = fields.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    doc_type = fields.get("doc_type") or ""
    topic = extract_text_field(fields.get("topic")).strip()

    source_type = infer_source_type(source, source_type_val)
    doc_id = compute_doc_id(source_type, publish_date, title, record_id)
    safe_id = safe_filename(doc_id)
    content_hash = compute_content_hash(body)
    dup_key = compute_duplicate_key(source, title, publish_date)

    lark_record_url = None
    if base_token and table_id and record_id:
        view_part = f"&view={view_id}" if view_id else ""
        lark_record_url = f"https://xxx.feishu.cn/base/{base_token}?table={table_id}{view_part}&row={record_id}"

    body_md_path = f"cleaned/{safe_id}.md"
    meta_json_path = f"metadata/{safe_id}.meta.json"

    # 审计
    audit_warnings = []
    audit_status = "passed"

    if not title:
        audit_warnings.append("missing_title")
    if not body:
        audit_warnings.append("missing_body")
    if not publish_date:
        audit_warnings.append("missing_publish_date")
    if body and len(body) < 50:
        audit_warnings.append("body_too_short")
    if needs_manual_review:
        audit_warnings.append("needs_manual_review")
        audit_status = "review_required"

    has_clean_status = clean_status is not None and clean_status != ""
    if bootstrap_mode and not has_clean_status:
        audit_warnings.append("missing_clean_status_bootstrap")

    return {
        "schema_version": SCHEMA_VERSION,
        "doc_id": doc_id,
        "corpus_collection": CORPUS_COLLECTION,
        "source_type": source_type,
        "source": source or "unknown",
        "title": title,
        "summary": summary,
        "body_md_path": body_md_path,
        "meta_json_path": meta_json_path,
        "lark_base_token": base_token,
        "lark_table_id": table_id,
        "lark_record_id": record_id,
        "lark_record_url": lark_record_url,
        "publish_date": publish_date,
        "issue_date": issue_date,
        "issue_no": issue_no,
        "total_issue_no": total_issue_no,
        "extracted_at": extracted_at,
        "synced_at": sync_ts,
        "clean_status": clean_status or "unknown",
        "split_status": split_status,
        "needs_manual_review": needs_manual_review,
        "manual_review_reason": manual_review_reason or None,
        "content_hash": content_hash,
        "duplicate_key": dup_key,
        "is_fact_safe": False,
        "rag_usage": "style_only",
        "fact_usage_allowed": False,
        "rule_candidate_allowed": True,
        "official_reference_allowed": False,
        "char_count": len(body),
        "paragraph_count": len([p for p in body.split("\n\n") if p.strip()]) if body else 0,
        "language": "zh",
        "tags": tags,
        "doc_type": doc_type,
        "topic": topic or None,
        "audit_status": audit_status,
        "audit_warnings": audit_warnings,
    }, body


# ─────────────────────────────────────────────
# 过滤
# ─────────────────────────────────────────────

def should_process(meta, strict_mode, bootstrap_mode, exclude_manual_review=False):
    if not meta["title"] or meta["char_count"] == 0:
        return False, "fatal_missing_title_or_body"

    if strict_mode:
        if meta["clean_status"] != "cleaned":
            return False, "strict_skipped_not_cleaned"
        if exclude_manual_review and meta.get("needs_manual_review"):
            return False, "manual_review_excluded"
        return True, None

    if bootstrap_mode:
        if meta["clean_status"] in ("cleaned", "unknown"):
            if exclude_manual_review and meta.get("needs_manual_review"):
                return False, "manual_review_excluded"
            return True, None
        return False, f"skipped_status_{meta['clean_status']}"

    # 默认 strict
    if meta["clean_status"] != "cleaned":
        return False, "skipped_not_cleaned"
    if exclude_manual_review and meta.get("needs_manual_review"):
        return False, "manual_review_excluded"
    return True, None


# ─────────────────────────────────────────────
# 写文件
# ─────────────────────────────────────────────

def write_markdown(filepath, meta, body):
    fm = [
        f"doc_id: {meta['doc_id']}",
        f"title: {meta['title']}",
        f"source: {meta['source']}",
        f"source_type: {meta['source_type']}",
        f"publish_date: {meta['publish_date'] or 'unknown'}",
        f"rag_usage: style_only",
        f"is_fact_safe: false",
        f"lark_record_id: {meta['lark_record_id']}",
        f"doc_type: {meta['doc_type']}",
    ]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("\n".join(fm) + "\n")
        f.write("---\n\n")
        f.write(body + "\n")


def write_metadata(filepath, meta):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def write_manifest(filepath, lines):
    with open(filepath, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def manifest_line_from_meta(meta):
    return {
        "doc_id": meta["doc_id"],
        "title": meta["title"],
        "body_md_path": meta["body_md_path"],
        "meta_json_path": meta["meta_json_path"],
        "content_hash": meta["content_hash"],
        "lark_record_id": meta["lark_record_id"],
        "source": meta["source"],
        "source_type": meta["source_type"],
        "publish_date": meta["publish_date"],
        "clean_status": meta["clean_status"],
        "rag_usage": meta["rag_usage"],
        "is_fact_safe": meta["is_fact_safe"],
        "audit_status": meta["audit_status"],
        "audit_warnings": meta["audit_warnings"],
    }


# ─────────────────────────────────────────────
# 批量构建入口
# ─────────────────────────────────────────────

def build_corpus(records, base_token, table_id, view_id, output_root,
                  strict_mode, bootstrap_mode, limit, dry_run,
                  exclude_manual_review=False):
    """
    核心构建入口。records 是 Base-like 记录列表。
    返回 (stats_dict, manifest_lines)。
    """
    if not strict_mode and not bootstrap_mode:
        strict_mode = True
    if strict_mode and bootstrap_mode:
        strict_mode = False

    stats = {
        "total_records": len(records),
        "processed": 0,
        "skipped": 0,
        "warnings": [],
        "errors": [],
    }

    if not dry_run:
        os.makedirs(os.path.join(output_root, "cleaned"), exist_ok=True)
        os.makedirs(os.path.join(output_root, "metadata"), exist_ok=True)
        os.makedirs(os.path.join(output_root, "manifests"), exist_ok=True)

    manifest_lines = []
    processed_count = 0

    for record in records:
        if limit > 0 and processed_count >= limit:
            break

        meta, body = build_metadata(record, base_token, table_id, view_id, bootstrap_mode)
        ok, reason = should_process(meta, strict_mode, bootstrap_mode, exclude_manual_review)

        if not ok:
            stats["skipped"] += 1
            stats["errors"].append(f"SKIP [{meta['lark_record_id']}]: {reason}")
            continue

        for w in meta["audit_warnings"]:
            stats["warnings"].append(f"WARN [{meta['lark_record_id']}]: {w}")

        if dry_run:
            stats["processed"] += 1
            manifest_lines.append(manifest_line_from_meta(meta))
            continue

        safe_id = safe_filename(meta["doc_id"])
        md_path = os.path.join(output_root, meta["body_md_path"])
        meta_path = os.path.join(output_root, meta["meta_json_path"])

        write_markdown(md_path, meta, body)
        write_metadata(meta_path, meta)

        stats["processed"] += 1
        processed_count += 1
        manifest_lines.append(manifest_line_from_meta(meta))

    if not dry_run and manifest_lines:
        write_manifest(
            os.path.join(output_root, "manifests", MANIFEST_FILENAME),
            manifest_lines,
        )

    return stats, manifest_lines
