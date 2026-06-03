#!/usr/bin/env python3
"""
mango-doc-writer v0.2.0 — Stage A2
从真实飞书 Base 只读同步到本地 corpus。

使用 lark-cli 读取 Base，标准化为 Base-like records，复用 corpus_builder 构建。

用法:
  python3 scripts/corpus/sync_from_lark_base.py \
    --base-token JZFrbEs7WaGUEdsVEzeci3vvnLe \
    --table-id tblo0JA25ejPj0LI \
    --output-root /tmp/mango_a2 \
    --bootstrap-missing-clean-status \
    --limit 5

  # dry-run:
  python3 scripts/corpus/sync_from_lark_base.py \
    --base-token JZFrbEs7WaGUEdsVEzeci3vvnLe \
    --table-id tblo0JA25ejPj0LI \
    --output-root /tmp/mango_a2 \
    --bootstrap-missing-clean-status \
    --limit 5 \
    --dry-run
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_builder import build_corpus, MANIFEST_FILENAME


# ─────────────────────────────────────────────
# 已知字段映射（field_name → field_id）
# ─────────────────────────────────────────────

KNOWN_FIELDS = {
    "时间": "fldgFMtR45",
    "链接": "fld8m0y2Ko",
    "备注": "fldHiWxwlw",
    "来源": "fldPqntJEs",
    "标题": "fldQzFNVdH",
    "概述": "flds7zsR4k",
    "正文": "fldxqsxIaG",
}

# lark-cli 返回的 data 数组索引与 KNOWN_FIELDS 一致
# 顺序: [时间, 链接, 备注, 来源, 标题, 概述, 正文]
DATA_INDEX_MAP = {
    "时间": 0,
    "链接": 1,
    "备注": 2,
    "来源": 3,
    "标题": 4,
    "概述": 5,
    "正文": 6,
}

# 可能存在的扩展字段
OPTIONAL_FIELDS = {
    "clean_status", "split_status", "needs_manual_review",
    "manual_review_reason", "source_type", "issue_no",
    "total_issue_no", "issue_date", "tags", "doc_type",
    "topic", "cleaned_at", "source_url", "raw_file_token",
    "cleaner", "sync_status", "last_synced_at",
}


def check_lark_cli():
    """检查 lark-cli 是否可用"""
    try:
        result = subprocess.run(
            ["lark-cli", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False, None


def resolve_field_ids(base_token, table_id, as_identity):
    """动态获取字段 ID 列表，尝试匹配已知字段名"""
    cmd = [
        "lark-cli", "base", "+field-list",
        "--base-token", base_token,
        "--table-id", table_id,
        "--as", as_identity,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None, result.stderr.strip()

        data = json.loads(result.stdout)
        items = data.get("data", {}).get("items", [])
        field_map = {}
        for item in items:
            name = item.get("field_name", "")
            fid = item.get("field_id", "")
            if name in KNOWN_FIELDS or name in OPTIONAL_FIELDS:
                field_map[name] = fid

        return field_map, None
    except Exception as e:
        return None, str(e)


def fetch_records(base_token, table_id, as_identity, page_size=100, offset=0, save_raw=False, output_root=None):
    """调用 lark-cli +record-list 获取一页记录"""
    cmd = [
        "lark-cli", "base", "+record-list",
        "--base-token", base_token,
        "--table-id", table_id,
        "--as", as_identity,
        "--limit", str(page_size),
        "--offset", str(offset),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return None, result.stderr.strip(), []

        raw_data = json.loads(result.stdout)

        # 保存原始返回
        if save_raw and output_root:
            debug_dir = os.path.join(output_root, "debug")
            os.makedirs(debug_dir, exist_ok=True)
            raw_path = os.path.join(debug_dir, f"raw_page_{offset}.json")
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)

        if not raw_data.get("ok"):
            return None, f"lark-cli returned ok=false", []

        inner = raw_data.get("data", {})
        rows = inner.get("data", [])
        field_ids = inner.get("field_id_list", [])
        record_id_list = inner.get("record_id_list", [])
        has_more = inner.get("has_more", False)
        total = inner.get("total", len(rows))

        return rows, None, {"has_more": has_more, "total": total, "field_ids": field_ids, "record_id_list": record_id_list}

    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}", []
    except subprocess.TimeoutExpired:
        return None, "lark-cli timeout (60s)", []
    except Exception as e:
        return None, str(e), []


def parse_row_to_record(row, record_id_list, field_ids, row_index):
    """将 lark-cli 返回的一行 data 转为 Base-like record"""
    # 确定此行的 record_id
    record_id = ""
    if row_index < len(record_id_list):
        record_id = record_id_list[row_index]

    # 动态映射 field_id → field_name
    FIELD_ID_TO_NAME = {
        "fldgFMtR45": "时间",
        "fld8m0y2Ko": "链接",
        "fldHiWxwlw": "备注",
        "fldPqntJEs": "来源",
        "fldQzFNVdH": "标题",
        "flds7zsR4k": "概述",
        "fldxqsxIaG": "正文",
        # v0.2.0 新增字段
        "fldDc4649Q": "clean_status",
        "fldcowiN8G": "split_status",
        "fldOH0y7xJ": "needs_manual_review",
        "fldoV74g4R": "manual_review_reason",
        "fldE2rgGjC": "source_type",
        "flduWyoH3B": "issue_date",
        "fldENUe7PL": "issue_no",
        "fldJ6YkRS5": "total_issue_no",
        "fld8sDsGRK": "cleaned_at",
        "fld8vjbxSs": "tags",
        "fldRBX0lkH": "doc_type",
        "fldTWalB2O": "topic",
        "fldtlhMz8f": "source_url",
        "fld0xGv7dc": "raw_file_token",
        "fldhnstL20": "cleaner",
        "fldzHeGEqo": "sync_status",
        "fldRVhnRcf": "last_synced_at",
    }

    # 动态构建 fields dict
    fields = {}
    for idx, fid in enumerate(field_ids):
        if idx < len(row):
            fname = FIELD_ID_TO_NAME.get(fid, fid)
            fields[fname] = row[idx]

    return {
        "record_id": record_id,
        "fields": fields,
    }


def fetch_all_records(base_token, table_id, as_identity, page_size, limit, save_raw, output_root):
    """分页获取所有记录"""
    all_records = []
    offset = 0
    total_fetched = 0

    while True:
        if limit > 0 and total_fetched >= limit:
            break

        rows, error, meta = fetch_records(
            base_token, table_id, as_identity,
            page_size=page_size, offset=offset,
            save_raw=save_raw, output_root=output_root,
        )

        if error:
            return None, error

        record_id_list = meta.get("record_id_list", [])
        field_ids = meta.get("field_ids", [])
        for i, row in enumerate(rows):
            all_records.append(parse_row_to_record(row, record_id_list, field_ids, i))
            total_fetched += 1
            if limit > 0 and total_fetched >= limit:
                break

        if not meta.get("has_more", False):
            break

        offset += page_size

    return all_records, None


def main():
    parser = argparse.ArgumentParser(description="A2: real Lark Base read-only sync")
    parser.add_argument("--base-token", required=True, help="Feishu Base app_token")
    parser.add_argument("--table-id", required=True, help="Feishu Base table_id")
    parser.add_argument("--view-id", default="", help="Feishu Base view_id (optional)")
    parser.add_argument("--output-root", required=True, help="Output root directory")
    parser.add_argument("--strict-cleaned-only", action="store_true")
    parser.add_argument("--bootstrap-missing-clean-status", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max records (0=unlimited)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--as", dest="as_identity", default="user", choices=["user", "bot"])
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--save-raw", action="store_true", help="Save raw lark-cli responses")
    parser.add_argument("--exclude-manual-review", action="store_true", help="Skip records with needs_manual_review=true")
    args = parser.parse_args()

    output_root = os.path.abspath(args.output_root)

    # 1. 检查 lark-cli
    ok, version = check_lark_cli()
    if not ok:
        print("❌ lark-cli not found. Please install: sudo npm install -g @larksuite/cli", file=sys.stderr)
        print("   Then authorize: lark-cli auth login", file=sys.stderr)
        sys.exit(2)

    print(f"✅ lark-cli found: {version}")

    # 2. 动态获取字段 ID（尝试）
    field_map, field_error = resolve_field_ids(args.base_token, args.table_id, args.as_identity)
    if field_error:
        print(f"⚠️  Could not resolve field IDs ({field_error}), using known mapping.")
    elif field_map:
        found = set(field_map.keys()) & set(KNOWN_FIELDS.keys())
        missing = set(KNOWN_FIELDS.keys()) - set(field_map.keys())
        print(f"✅ Resolved fields: {found}")
        if missing:
            print(f"⚠️  Missing fields: {missing} (will be None)")

    # 3. 获取记录
    print(f"\n📡 Fetching records from Base (table={args.table_id}, as={args.as_identity}, limit={args.limit or 'all'})...")

    records, fetch_error = fetch_all_records(
        base_token=args.base_token,
        table_id=args.table_id,
        as_identity=args.as_identity,
        page_size=args.page_size,
        limit=args.limit,
        save_raw=args.save_raw,
        output_root=output_root,
    )

    if fetch_error:
        print(f"❌ Failed to fetch records: {fetch_error}", file=sys.stderr)
        print("\nPossible causes:", file=sys.stderr)
        print("  1. lark-cli not authorized → run: lark-cli auth login", file=sys.stderr)
        print("  2. Base token or table_id incorrect", file=sys.stderr)
        print("  3. Insufficient permissions for user identity", file=sys.stderr)
        print("  4. Network issue", file=sys.stderr)
        sys.exit(2)

    if not records:
        print("⚠️  No records fetched from Base.")
        sys.exit(0)

    print(f"✅ Fetched {len(records)} records")

    # 4. 构建 corpus
    stats, manifest_lines = build_corpus(
        records=records,
        base_token=args.base_token,
        table_id=args.table_id,
        view_id=args.view_id,
        output_root=output_root,
        strict_mode=args.strict_cleaned_only,
        bootstrap_mode=args.bootstrap_missing_clean_status,
        limit=args.limit,
        dry_run=args.dry_run,
        exclude_manual_review=args.exclude_manual_review,
    )

    mode = "bootstrap" if args.bootstrap_missing_clean_status else "strict"
    label = f"{'DRY-RUN ' if args.dry_run else ''}SYNC"
    print(f"\n{'='*60}")
    print(f"{label} SUMMARY (mode={mode})")
    print(f"{'='*60}")
    print(f"  Total records:   {stats['total_records']}")
    print(f"  Processed:       {stats['processed']}")
    print(f"  Skipped:         {stats['skipped']}")
    print(f"  Warnings:        {len(stats['warnings'])}")
    if stats["errors"]:
        print(f"  Skips:")
        for e in stats["errors"][:20]:
            print(f"    {e}")
    if stats["warnings"]:
        print(f"  Warnings:")
        for w in stats["warnings"][:20]:
            print(f"    {w}")
    if len(stats["errors"]) > 20:
        print(f"    ... and {len(stats['errors']) - 20} more skips")
    if len(stats["warnings"]) > 20:
        print(f"    ... and {len(stats['warnings']) - 20} more warnings")
    print(f"{'='*60}")

    if not args.dry_run:
        md_count = len([f for f in os.listdir(os.path.join(output_root, "cleaned")) if f.endswith(".md")])
        meta_count = len([f for f in os.listdir(os.path.join(output_root, "metadata")) if f.endswith(".meta.json")])
        manifest_path = os.path.join(output_root, "manifests", MANIFEST_FILENAME)
        manifest_count = sum(1 for _ in open(manifest_path)) if os.path.exists(manifest_path) else 0
        print(f"\n📁 Output:")
        print(f"  cleaned/*.md:     {md_count}")
        print(f"  metadata/*.json:  {meta_count}")
        print(f"  manifest lines:   {manifest_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
