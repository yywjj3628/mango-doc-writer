#!/usr/bin/env python3
"""
B4.1: 从旧 60 篇芒果日志生成 v0.2 chunks + Qdrant payload。
不连接 Qdrant，不写 collection。
"""
import json, os, hashlib, uuid, re, yaml
from datetime import datetime, timezone, timedelta

# Config
CLEANED_DIR = 'corpus/mango_style_docs/cleaned'
MANIFEST = 'corpus/mango_style_docs/manifest.yaml'
OUTPUT = 'corpus/mango_style_docs/staging/v0.2.0-b4-legacy-mango-60/qdrant_payload'
SNAPSHOT_ID = 'v0.2.0-b4-legacy-mango-60'
BATCH_ID = 'v0.2.0-b4.1-legacy-mango-60'
TARGET_COLLECTION = 'mango_style_docs_v020_candidate'

# Chunk strategy (same as B3.6)
TARGET_CHARS = 900
MAX_CHARS = 1200
MIN_CHARS = 120

TZ_CN = timezone(timedelta(hours=8))

# Doc type mapping
DOC_TYPE_MAP = {
    '新闻稿': 'mango_rizhi_news',
    '领导讲话': 'leader_speech',
    '活动稿': 'activity_news',
    '党建材料': 'governance_news',
    '通报': 'governance_news',
}

STYLE_WEIGHT_MAP = {
    'leader_speech': 'high',
    'mango_rizhi_news': 'high',
    'activity_news': 'high',
    'governance_news': 'medium',
    'other': 'medium',
}

TIER_MAP = {
    'leader_speech': 'core',
    'mango_rizhi_news': 'core',
    'activity_news': 'normal',
    'governance_news': 'normal',
    'other': 'archive',
}

def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def chunk_text(body, target=TARGET_CHARS, max_c=MAX_CHARS, min_c=MIN_CHARS):
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [body.strip()]
    if len(body) <= max_c:
        return [body.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(para) > max_c:
            if current:
                chunks.append(current.strip())
                current = ""
            sentences = re.split(r'(?<=[。！？；\n])', para)
            for sent in sentences:
                if current and len(current) + len(sent) > max_c:
                    chunks.append(current.strip())
                    current = sent
                else:
                    current += sent
        elif current and len(current) + len(para) + 2 > max_c:
            chunks.append(current.strip())
            current = para
        else:
            if current:
                current += "\n\n" + para
            else:
                current = para
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [body.strip()]

# Main
os.makedirs(OUTPUT, exist_ok=True)

# Load manifest
with open(MANIFEST) as f:
    manifest = yaml.safe_load(f)
entries = manifest if isinstance(manifest, list) else manifest.get('documents', [])

print(f"Manifest entries: {len(entries)}")

chunks_out = []
payloads_out = []
total_chunks = 0
doc_count = 0

for entry in entries:
    filename = entry.get('file', '')
    title = entry.get('title', '')
    source = entry.get('source', '')
    date = entry.get('date', '')
    url = entry.get('url', '')
    old_doc_type = entry.get('doc_type', '')
    category = entry.get('category', '')
    tags = entry.get('tags', [])
    char_count = entry.get('char_count', 0)

    # Read body
    fpath = os.path.join(CLEANED_DIR, filename)
    if not os.path.exists(fpath):
        print(f"WARNING: {filename} not found, skipping")
        continue
    with open(fpath) as f:
        body = f.read()

    doc_count += 1
    content_hash = sha256(body)

    # Generate doc_id
    sha8 = sha256(title + filename + date + content_hash)[:8]
    doc_id = f"legacy_mango_{date}_{sha8}"

    # Map doc_type
    doc_type = DOC_TYPE_MAP.get(old_doc_type, 'other')
    style_weight = STYLE_WEIGHT_MAP.get(doc_type, 'medium')
    corpus_tier = TIER_MAP.get(doc_type, 'archive')

    # Chunk
    text_chunks = chunk_text(body)
    n_chunks = len(text_chunks)
    total_chunks += n_chunks

    for i, chunk_text_str in enumerate(text_chunks):
        chunk_id = f"{doc_id}_chunk{i:03d}"
        chunk_hash = sha256(chunk_text_str)
        chunk_char_count = len(chunk_text_str)

        chunks_out.append({
            'chunk_id': chunk_id,
            'doc_id': doc_id,
            'legacy_filename': filename,
            'chunk_index': i,
            'total_chunks': n_chunks,
            'text': chunk_text_str,
            'char_count': chunk_char_count,
            'content_hash': content_hash,
            'chunk_hash': chunk_hash,
        })

        payloads_out.append({
            'id': str(uuid.uuid4()),
            'text': chunk_text_str,
            'metadata': {
                'title': title,
                'filename': filename,
                'doc_id': doc_id,
                'legacy_source': True,
                'legacy_filename': filename,
                'lark_record_id': None,
                'source_family': 'hunan_mango',
                'source': source,
                'source_type': 'official_account',
                'doc_type': doc_type,
                'proposed_doc_subtype': category if category else doc_type,
                'style_weight': style_weight,
                'corpus_tier': corpus_tier,
                'publish_date': date,
                'url': url,
                'tags': tags,
                'content_hash': content_hash,
                'chunk_hash': chunk_hash,
                'chunk_index': i,
                'total_chunks': n_chunks,
                'char_count': chunk_char_count,
                'collection': 'mango_style_docs',
                'target_collection': TARGET_COLLECTION,
                'snapshot_id': SNAPSHOT_ID,
                'batch_id': BATCH_ID,
                'rag_usage': 'style_only',
                'is_fact_safe': False,
                'fact_usage_allowed': False,
                'official_reference_allowed': False,
                'rule_candidate_allowed': True,
                'use_for': ['style', 'opening', 'rhythm'],
            }
        })

# Write chunks
with open(f'{OUTPUT}/chunks-v0.2.0-b4.1-legacy-mango-60.jsonl', 'w') as f:
    for c in chunks_out:
        f.write(json.dumps(c, ensure_ascii=False) + '\n')

# Write payloads
with open(f'{OUTPUT}/payload-v0.2.0-b4.1-legacy-mango-60.jsonl', 'w') as f:
    for p in payloads_out:
        f.write(json.dumps(p, ensure_ascii=False) + '\n')

# Summary
summary = {
    'input_documents': doc_count,
    'total_chunks': total_chunks,
    'avg_chunks_per_doc': round(total_chunks/doc_count, 2) if doc_count else 0,
    'generated_at': datetime.now(TZ_CN).isoformat(),
    'batch_id': BATCH_ID,
    'snapshot_id': SNAPSHOT_ID,
    'target_collection': TARGET_COLLECTION,
}
with open(f'{OUTPUT}/payload-summary-v0.2.0-b4.1-legacy-mango-60.json', 'w') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"Documents: {doc_count}")
print(f"Chunks: {total_chunks}")
print(f"Avg chunks/doc: {total_chunks/doc_count:.2}")
print(f"Output: {OUTPUT}/")
print("DONE")
