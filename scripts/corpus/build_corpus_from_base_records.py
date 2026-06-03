#!/usr/bin/env python3
"""
mango-doc-writer v0.2.0 — Stage A1
从 fixture JSON 构建 corpus（复用 corpus_builder 共享模块）。

用法:
  python3 scripts/corpus/build_corpus_from_base_records.py \
    --fixture tests/fixtures/lark_base_records_siqing_sample.json \
    --output-root /tmp/output \
    --strict-cleaned-only
"""
import argparse
import json
import os
import sys

# 共享模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_builder import build_corpus, MANIFEST_FILENAME


def main():
    parser = argparse.ArgumentParser(description="A1: fixture-driven corpus build")
    parser.add_argument("--fixture", required=True, help="Path to fixture JSON")
    parser.add_argument("--output-root", required=True, help="Output root directory")
    parser.add_argument("--strict-cleaned-only", action="store_true")
    parser.add_argument("--bootstrap-missing-clean-status", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max records (0=unlimited)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(os.path.abspath(args.fixture), "r", encoding="utf-8") as f:
        data = json.load(f)

    base_token = data.get("_base_token", "")
    table_id = data.get("_table_id", "")
    view_id = data.get("_view_id", "")
    records = data.get("records", [])

    stats, manifest_lines = build_corpus(
        records=records,
        base_token=base_token,
        table_id=table_id,
        view_id=view_id,
        output_root=os.path.abspath(args.output_root),
        strict_mode=args.strict_cleaned_only,
        bootstrap_mode=args.bootstrap_missing_clean_status,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    mode = "bootstrap" if args.bootstrap_missing_clean_status else "strict"
    print_summary(f"{'DRY-RUN ' if args.dry_run else ''}BUILD", mode, stats)
    return 0


def print_summary(label, mode, stats):
    print(f"\n{'='*60}")
    print(f"{label} SUMMARY (mode={mode})")
    print(f"{'='*60}")
    print(f"  Total records:   {stats['total_records']}")
    print(f"  Processed:       {stats['processed']}")
    print(f"  Skipped:         {stats['skipped']}")
    print(f"  Warnings:        {len(stats['warnings'])}")
    for e in stats.get("errors", []):
        print(f"    {e}")
    for w in stats.get("warnings", []):
        print(f"    {w}")
    print(f"{'='*60}")


if __name__ == "__main__":
    sys.exit(main())
