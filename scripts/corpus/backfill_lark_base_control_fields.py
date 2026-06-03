#!/usr/bin/env python3
"""
mango-doc-writer v0.2.0 — Stage B1.1
VPS-side Base control field backfill.

对飞书 Base 已有记录做最小控制字段回填，使 strict-cleaned-only 模式可消费。
这是一次迁移/治理动作，不是日常同步链路。

用法:
  # dry-run (默认)
  python3 scripts/corpus/backfill_lark_base_control_fields.py \
    --base-token JZFrbEs7WaGUEdsVEzeci3vvnLe \
    --table-id tblo0JA25ejPj0LI \
    --limit 20 --dry-run --as user

  # apply
  python3 scripts/corpus/backfill_lark_base_control_fields.py \
    --base-token JZFrbEs7WaGUEdsVEzeci3vvnLe \
    --table-id tblo0JA25ejPj0LI \
    --limit 20 --apply --readback --as user
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

TZ_CN = timezone(timedelta(hours=8))

# ─────────────────────────────────────────────
# Field ID mapping (from Base schema)
# ─────────────────────────────────────────────
FIELD_ID_TO_NAME = {
    "fldgFMtR45": "时间",
    "fld0xGv7dc": "raw_file_token",
    "fld8m0y2Ko": "链接",
    "fld8sDsGRK": "cleaned_at",
    "fld8vjbxSs": "tags",
    "fldcowiN8G": "split_status",
    "fldDc4649Q": "clean_status",
    "fldE2rgGjC": "source_type",
    "fldENUe7PL": "issue_no",
    "fldHiWxwlw": "备注",
    "fldhnstL20": "cleaner",
    "fldJ6YkRS5": "total_issue_no",
    "fldOH0y7xJ": "needs_manual_review",
    "fldoV74g4R": "manual_review_reason",
    "fldPqntJEs": "来源",
    "fldQzFNVdH": "标题",
    "fldRBX0lkH": "doc_type",
    "fldRVhnRcf": "last_synced_at",
    "flds7zsR4k": "概述",
    "fldtlhMz8f": "source_url",
    "fldTWalB2O": "topic",
    "flduWyoH3B": "issue_date",
    "fldxqsxIaG": "正文",
    "fldzHeGEqo": "sync_status",
}

NAME_TO_FIELD_ID = {v: k for k, v in FIELD_ID_TO_NAME.items()}

# 控制字段 (允许回填)
CONTROL_FIELDS = {
    "clean_status", "source_type", "needs_manual_review",
    "split_status", "manual_review_reason", "cleaned_at",
}


def check_lark_cli():
    try:
        r = subprocess.run(["lark-cli", "--version"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0, r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def fetch_records(base_token, table_id, as_identity, page_size=100, limit=0):
    """分页获取所有记录"""
    all_records = []
    offset = 0
    total_fetched = 0

    while True:
        if limit > 0 and total_fetched >= limit:
            break
        cmd = [
            "lark-cli", "base", "+record-list",
            "--base-token", base_token,
            "--table-id", table_id,
            "--as", as_identity,
            "--limit", str(min(page_size, limit - total_fetched if limit > 0 else page_size)),
            "--offset", str(offset),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return None, f"lark-cli error: {r.stderr.strip()}"
        data = json.loads(r.stdout)
        if not data.get("ok"):
            return None, f"lark-cli ok=false"

        inner = data.get("data", {})
        rows = inner.get("data", [])
        field_ids = inner.get("field_id_list", [])
        record_ids = inner.get("record_id_list", [])
        has_more = inner.get("has_more", False)

        for i, row in enumerate(rows):
            rid = record_ids[i] if i < len(record_ids) else ""
            fields = {}
            for j, fid in enumerate(field_ids):
                if j < len(row):
                    fname = FIELD_ID_TO_NAME.get(fid, fid)
                    fields[fname] = row[j]
            all_records.append({"record_id": rid, "fields": fields})
            total_fetched += 1
            if limit > 0 and total_fetched >= limit:
                break

        if not has_more:
            break
        offset += page_size

    return all_records, None


def extract_text(field):
    if field is None:
        return ""
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        return "".join(p.get("text", "") for p in field if isinstance(p, dict))
    return str(field)


def extract_first(field):
    if field is None:
        return ""
    if isinstance(field, list):
        return field[0] if field else ""
    return str(field)


def has_directory_noise(text):
    """检查正文是否含目录噪音"""
    if not text:
        return False
    head = text[:500]
    if "内容提要" in head:
        return True
    bullet_count = head.count("●")
    if bullet_count >= 5:
        return True
    return False


def infer_control_fields(fields):
    """根据记录字段推断控制字段值"""
    title = extract_text(fields.get("标题")).strip()
    body = extract_text(fields.get("正文")).strip()
    source = extract_first(fields.get("来源")).strip()

    patch = {}
    reasons = []

    # --- clean_status ---
    if title and body:
        patch["clean_status"] = "cleaned"
    elif not title and not body and not source:
        patch["clean_status"] = "rejected"
    else:
        patch["clean_status"] = "raw"

    # --- source_type ---
    if "司情" in source:
        patch["source_type"] = "weekly_siqing"
    elif source in ("湖南广播电视台办公室", "湖南广电党建", "清风芒果", "电广传媒917"):
        patch["source_type"] = "official_account"
    elif source:
        patch["source_type"] = "web_article"
    else:
        patch["source_type"] = "internal_doc"
        reasons.append("来源为空，source_type 需复核")

    # --- needs_manual_review ---
    needs_review = False
    if not title:
        needs_review = True
        reasons.append("标题为空")
    if not body:
        needs_review = True
        reasons.append("正文为空")
    if not source:
        needs_review = True
        reasons.append("来源为空")
    if body and len(body) < 80:
        needs_review = True
        reasons.append(f"正文过短({len(body)}字)")
    if has_directory_noise(body):
        needs_review = True
        reasons.append("正文疑似目录噪音")

    patch["needs_manual_review"] = needs_review

    # --- manual_review_reason ---
    if reasons:
        patch["manual_review_reason"] = "; ".join(reasons)
    else:
        patch["manual_review_reason"] = None

    # --- split_status ---
    if "司情" in source:
        patch["split_status"] = "split"
    elif source in ("湖南广播电视台办公室", "湖南广电党建", "清风芒果", "电广传媒917"):
        patch["split_status"] = "not_needed"
    elif not title or not body:
        patch["split_status"] = "not_split"
    else:
        patch["split_status"] = "not_needed"

    # --- cleaned_at ---
    if patch["clean_status"] == "cleaned":
        patch["cleaned_at"] = datetime.now(TZ_CN).strftime("%Y/%m/%d %H:%M")
    else:
        patch["cleaned_at"] = None

    return patch, reasons


def build_upsert_json(patch):
    """将 patch dict 转为 lark-cli +record-upsert --json 格式"""
    rec = {}
    for fname, val in patch.items():
        fid = NAME_TO_FIELD_ID.get(fname)
        if not fid:
            continue
        if fname == "clean_status":
            rec[fid] = val  # single select: string
        elif fname == "source_type":
            rec[fid] = val
        elif fname == "needs_manual_review":
            rec[fid] = bool(val)  # checkbox: boolean
        elif fname == "split_status":
            rec[fid] = val
        elif fname == "manual_review_reason":
            rec[fid] = val if val else None
        elif fname == "cleaned_at":
            # datetime: 需要毫秒时间戳或保持 None
            if val:
                try:
                    dt = datetime.strptime(val, "%Y/%m/%d %H:%M").replace(tzinfo=TZ_CN)
                    rec[fid] = int(dt.timestamp() * 1000)
                except ValueError:
                    rec[fid] = None
            else:
                rec[fid] = None
    return rec


def update_record(base_token, table_id, record_id, patch_json, as_identity):
    """用 lark-cli +record-upsert 更新单条记录"""
    cmd = [
        "lark-cli", "base", "+record-upsert",
        "--base-token", base_token,
        "--table-id", table_id,
        "--record-id", record_id,
        "--as", as_identity,
        "--json", json.dumps(patch_json, ensure_ascii=False),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return False, r.stderr.strip()
    data = json.loads(r.stdout) if r.stdout.strip() else {}
    return data.get("ok", False), data


def readback_record(base_token, table_id, record_id, as_identity):
    """写入后读回验证"""
    cmd = [
        "lark-cli", "base", "+record-get",
        "--base-token", base_token,
        "--table-id", table_id,
        "--record-id", record_id,
        "--as", as_identity,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return None
    data = json.loads(r.stdout) if r.stdout.strip() else {}
    if not data.get("ok"):
        return None
    inner = data.get("data", {})
    fields_raw = inner.get("fields", {})
    # 转换 field_id → field_name
    result = {}
    for fid, val in fields_raw.items():
        fname = FIELD_ID_TO_NAME.get(fid, fid)
        result[fname] = val
    return result


def main():
    parser = argparse.ArgumentParser(description="B1.1: Base control field backfill")
    parser.add_argument("--base-token", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--as", dest="as_identity", default="user", choices=["user", "bot"])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--only-empty-clean-status", type=bool, default=True)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--save-plan", default=None)
    parser.add_argument("--readback", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("⚠️  Neither --dry-run nor --apply specified. Defaulting to --dry-run.")
        args.dry_run = True

    ok, ver = check_lark_cli()
    if not ok:
        print("❌ lark-cli not found", file=sys.stderr)
        sys.exit(2)
    print(f"✅ lark-cli: {ver}")

    # 1. Fetch records
    print(f"\n📡 Fetching records (limit={args.limit or 'all'})...")
    records, err = fetch_records(args.base_token, args.table_id, args.as_identity,
                                 args.page_size, args.limit)
    if err:
        print(f"❌ Fetch failed: {err}", file=sys.stderr)
        sys.exit(2)
    print(f"✅ Fetched {len(records)} records")

    # 2. Build backfill plan
    plan = []
    skip_existing = 0
    for rec in records:
        fields = rec["fields"]
        rid = rec["record_id"]
        existing_cs = fields.get("clean_status")

        if args.only_empty_clean_status and existing_cs and not args.overwrite:
            skip_existing += 1
            continue

        patch, reasons = infer_control_fields(fields)
        plan.append({
            "record_id": rid,
            "title": extract_text(fields.get("标题")).strip()[:60],
            "source": extract_first(fields.get("来源")).strip(),
            "existing_clean_status": existing_cs,
            "patch": patch,
            "reasons": reasons,
        })

    print(f"\n📊 Backfill plan:")
    print(f"  Total fetched:    {len(records)}")
    print(f"  Already filled:   {skip_existing}")
    print(f"  To backfill:      {len(plan)}")

    # Clean status distribution
    cs_dist = {}
    st_dist = {}
    review_list = []
    for item in plan:
        cs = item["patch"]["clean_status"]
        cs_dist[cs] = cs_dist.get(cs, 0) + 1
        st = item["patch"]["source_type"]
        st_dist[st] = st_dist.get(st, 0) + 1
        if item["patch"]["needs_manual_review"]:
            review_list.append(item)

    print(f"\n  clean_status distribution:")
    for k, v in sorted(cs_dist.items()):
        print(f"    {k}: {v}")
    print(f"\n  source_type distribution:")
    for k, v in sorted(st_dist.items()):
        print(f"    {k}: {v}")
    print(f"\n  needs_manual_review=true: {len(review_list)}")

    # Save plan
    if args.save_plan:
        os.makedirs(os.path.dirname(args.save_plan) or ".", exist_ok=True)
        with open(args.save_plan, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Plan saved: {args.save_plan}")

    if args.dry_run:
        print(f"\n🔍 DRY-RUN complete. No records were modified.")
        print(f"   Use --apply to write to Base.")
        # Show first 5 plan items
        for item in plan[:5]:
            print(f"\n  [{item['record_id']}] {item['title']}")
            print(f"    → clean_status={item['patch']['clean_status']}, source_type={item['patch']['source_type']}")
            print(f"    → needs_manual_review={item['patch']['needs_manual_review']}, split_status={item['patch']['split_status']}")
            if item['reasons']:
                print(f"    ⚠️  {', '.join(item['reasons'])}")
        if len(plan) > 5:
            print(f"\n  ... and {len(plan) - 5} more")
        return 0

    # 3. Apply
    if not plan:
        print("\n✅ Nothing to backfill.")
        return 0

    print(f"\n🚀 Applying backfill ({len(plan)} records, batch-size={args.batch_size})...")
    success = 0
    failed = 0
    for i, item in enumerate(plan):
        rid = item["record_id"]
        patch_json = build_upsert_json(item["patch"])
        ok, result = update_record(args.base_token, args.table_id, rid, patch_json, args.as_identity)
        if ok:
            success += 1
            print(f"  ✅ [{i+1}/{len(plan)}] {rid} → {item['patch']['clean_status']}")
        else:
            failed += 1
            print(f"  ❌ [{i+1}/{len(plan)}] {rid}: {result}")
        # Rate limit: small delay between writes
        if (i + 1) % args.batch_size == 0:
            import time
            time.sleep(1)

    print(f"\n📊 Apply result:")
    print(f"  Success: {success}")
    print(f"  Failed:  {failed}")

    # 4. Readback verification
    if args.readback and success > 0:
        print(f"\n🔍 Readback verification (checking {min(success, 10)} records)...")
        verify_records = [item for item in plan][:10]
        verified_cleaned = 0
        for item in verify_records:
            rid = item["record_id"]
            rb = readback_record(args.base_token, args.table_id, rid, args.as_identity)
            if not rb:
                print(f"  ⚠️  [{rid}] readback failed")
                continue
            cs = rb.get("clean_status")
            st = rb.get("source_type")
            nmr = rb.get("needs_manual_review")
            title = extract_text(rb.get("标题")).strip()[:40]
            print(f"  [{rid}] clean_status={cs}, source_type={st}, needs_manual_review={nmr} | {title}")
            if cs == "cleaned":
                verified_cleaned += 1
        print(f"\n  Verified clean_status=cleaned: {verified_cleaned}/{len(verify_records)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
