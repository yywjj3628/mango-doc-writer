#!/usr/bin/env python3
"""
B3.6: 从 snapshot 生成本地 chunk + Qdrant payload JSONL。
不连接 Qdrant，不写 collection，不调用 embedding。
"""
import json, os, hashlib, uuid, re, sys
from datetime import datetime, timezone, timedelta

# Config
SNAPSHOT = 'corpus/mango_style_docs/staging/v0.2.0-b3-siqing-299'
OUTPUT = f'{SNAPSHOT}/qdrant_payload'
BATCH_ID = 'v0.2.0-b3.4-siqing-299'
SNAPSHOT_ID = 'v0.2.0-b3-siqing-299'
CANDIDATE_COLLECTION = 'mango_style_docs_v020_siqing_299_candidate'

# Chunk strategy
TARGET_CHARS = 900
MAX_CHARS = 1200
MIN_CHARS = 120

TZ_CN = timezone(timedelta(hours=8))

def chunk_text(body, target=TARGET_CHARS, max_c=MAX_CHARS, min_c=MIN_CHARS):
    """Paragraph-based chunking."""
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [body.strip()]
    
    # Short text: single chunk
    if len(body) <= max_c:
        return [body.strip()]
    
    chunks = []
    current = ""
    
    for para in paragraphs:
        if len(para) > max_c:
            # Single paragraph too long: split by sentences
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

def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# Main
os.makedirs(OUTPUT, exist_ok=True)

# Load manifest
manifest = []
with open(f'{SNAPSHOT}/manifests/manifest-v0.2.0-b3.4-siqing-299.jsonl') as f:
    for line in f:
        manifest.append(json.loads(line))

print(f"Input documents: {len(manifest)}")

chunks_out = []
payloads_out = []
total_chunks = 0

for r in manifest:
    doc_id = r.get('doc_id','')
    lark_record_id = r.get('lark_record_id','')
    title = r.get('title','')
    
    # Load metadata
    meta_path = f'{SNAPSHOT}/metadata/{doc_id}.meta.json'
    with open(meta_path) as f:
        meta = json.load(f)
    
    # Load body
    body_path = f'{SNAPSHOT}/cleaned/{doc_id}.md'
    with open(body_path) as f:
        body = f.read()
    
    # Chunk
    text_chunks = chunk_text(body)
    n_chunks = len(text_chunks)
    total_chunks += n_chunks
    
    for i, chunk_text_str in enumerate(text_chunks):
        chunk_id = f"{doc_id}_chunk{i:03d}"
        chunk_hash = sha256(chunk_text_str)
        char_count = len(chunk_text_str)
        
        # Chunk record
        chunks_out.append({
            'chunk_id': chunk_id,
            'doc_id': doc_id,
            'lark_record_id': lark_record_id,
            'chunk_index': i,
            'total_chunks': n_chunks,
            'text': chunk_text_str,
            'char_count': char_count,
            'content_hash': meta.get('content_hash',''),
            'chunk_hash': chunk_hash,
        })
        
        # Qdrant payload
        payloads_out.append({
            'id': str(uuid.uuid4()),
            'text': chunk_text_str,
            'metadata': {
                'title': title,
                'filename': f'{doc_id}.md',
                'doc_id': doc_id,
                'lark_record_id': lark_record_id,
                'source_family': 'dianguang_media',
                'source': '电广传媒司情',
                'source_type': 'weekly_siqing',
                'doc_type': 'siqing_news',
                'proposed_doc_subtype': meta.get('proposed_doc_subtype','general_news'),
                'corpus_tier': meta.get('corpus_tier','normal'),
                'style_weight': 'medium',
                'publish_date': meta.get('publish_date',''),
                'content_hash': meta.get('content_hash',''),
                'chunk_hash': chunk_hash,
                'chunk_index': i,
                'total_chunks': n_chunks,
                'collection': 'mango_style_docs',
                'candidate_collection': CANDIDATE_COLLECTION,
                'snapshot_id': SNAPSHOT_ID,
                'batch_id': BATCH_ID,
                'rag_usage': 'style_only',
                'is_fact_safe': False,
                'fact_usage_allowed': False,
                'official_reference_allowed': False,
                'rule_candidate_allowed': True,
                'use_for': ['style'],
            }
        })

# Write chunks JSONL
with open(f'{OUTPUT}/chunks-v0.2.0-b3.6-siqing-299.jsonl', 'w') as f:
    for c in chunks_out:
        f.write(json.dumps(c, ensure_ascii=False) + '\n')

# Write payloads JSONL
with open(f'{OUTPUT}/payload-v0.2.0-b3.6-siqing-299.jsonl', 'w') as f:
    for p in payloads_out:
        f.write(json.dumps(p, ensure_ascii=False) + '\n')

# Summary
summary = {
    'input_documents': len(manifest),
    'total_chunks': total_chunks,
    'avg_chunks_per_doc': round(total_chunks/len(manifest), 2),
    'generated_at': datetime.now(TZ_CN).isoformat(),
    'batch_id': BATCH_ID,
    'snapshot_id': SNAPSHOT_ID,
    'candidate_collection': CANDIDATE_COLLECTION,
}
with open(f'{OUTPUT}/payload-summary-v0.2.0-b3.6-siqing-299.json', 'w') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"Total chunks: {total_chunks}")
print(f"Avg chunks/doc: {total_chunks/len(manifest):.2}")
print(f"Output: {OUTPUT}/")
print("DONE")
