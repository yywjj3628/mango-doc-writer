#!/usr/bin/env python3
"""
mango_style_docs 自定义 ingest 脚本。
在 RAG Docker 容器内执行（依赖 bge-m3 embedding + qdrant-client）。
功能：
1. 读取 cleaned/*.md，解析 YAML front matter
2. 按段落切分（600-1000字/ chunk，overlap 100-150字）
3. 每 chunk 继承原文 metadata + 增加 chunk_index/total_chunks/char_count/collection/ingest_time
4. embedding → 写入 Qdrant collection mango_style_docs
"""
import os, sys, re, yaml, json, hashlib, uuid
from datetime import datetime, timezone, timedelta

# ---- 配置 ----
CLEANED_DIR = "/data/jiuyou_docs/style_docs"  # Docker 容器内挂载路径
COLLECTION = "mango_style_docs"
QDRANT_HOST = "rag-qdrant"
QDRANT_PORT = 6333
CHUNK_MIN = 500
CHUNK_MAX = 1000
OVERLAP = 120

TZ_CN = timezone(timedelta(hours=8))

def parse_front_matter(text):
    """解析 YAML front matter，返回 (metadata_dict, body_text)"""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1))
    except:
        meta = {}
    body = text[m.end():]
    return meta or {}, body

def chunk_text(body, title, chunk_min=CHUNK_MIN, chunk_max=CHUNK_MAX, overlap=OVERLAP):
    """按段落切分正文，保留完整段落，每 chunk 加入标题"""
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [body.strip()]
    
    chunks = []
    current = ""
    
    for para in paragraphs:
        # 如果当前 chunk + 新段落超过上限，先保存当前 chunk
        if current and len(current) + len(para) + 2 > chunk_max:
            chunks.append(current.strip())
            # overlap: 取当前 chunk 末尾 overlap 字符
            if overlap > 0 and len(current) > overlap:
                current = current[-overlap:] + "\n\n" + para
            else:
                current = para
        else:
            if current:
                current += "\n\n" + para
            else:
                current = para
    
    if current.strip():
        chunks.append(current.strip())
    
    # 如果某个 chunk 太短，合并到前一个
    merged = []
    for c in chunks:
        if merged and len(c) < chunk_min and len(merged[-1]) + len(c) + 2 <= chunk_max:
            merged[-1] += "\n\n" + c
        else:
            merged.append(c)
    
    # 每 chunk 前加标题
    result = []
    for c in merged:
        if title and not c.startswith(title):
            result.append(f"# {title}\n\n{c}")
        else:
            result.append(c)
    
    return result

def make_point_id(filename, idx):
    """确定性 point_id"""
    raw = f"{filename}_chunk_{idx}"
    return abs(int(hashlib.md5(raw.encode()).hexdigest()[:16], 16))

def main():
    import qdrant_client
    from qdrant_client.models import PointStruct, VectorParams, Distance
    
    # 连接 Qdrant
    client = qdrant_client.QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # 创建 collection（如不存在）
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        print(f"✅ 创建 collection: {COLLECTION}")
    else:
        print(f"⚠️  collection 已存在: {COLLECTION}")
    
    # 加载 embedding 模型
    sys.path.insert(0, "/app")
    from app.embedding import get_embedding_model
    embed_model = get_embedding_model()
    print("✅ embedding 模型加载完成")
    
    # 读取所有 cleaned/*.md
    files = sorted([f for f in os.listdir(CLEANED_DIR) if f.endswith('.md')])
    print(f"\n📂 找到 {len(files)} 个文件")
    
    all_points = []
    stats = {"total_files": 0, "total_chunks": 0, "failed": 0, "doc_types": {}, "categories": {}}
    
    for fname in files:
        fpath = os.path.join(CLEANED_DIR, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            raw = f.read()
        
        meta, body = parse_front_matter(raw)
        title = meta.get('title', '')
        doc_type = meta.get('doc_type', '')
        category = meta.get('category', '')
        source = meta.get('source', '')
        date = meta.get('date', '')
        url = meta.get('url', '')
        organization = meta.get('organization', '')
        tags = meta.get('tags', [])
        use_for = meta.get('use_for', [])
        is_fact_safe = meta.get('is_fact_safe', False)
        
        if not body.strip():
            stats["failed"] += 1
            continue
        
        chunks = chunk_text(body, title)
        stats["total_files"] += 1
        stats["total_chunks"] += len(chunks)
        stats["doc_types"][doc_type] = stats["doc_types"].get(doc_type, 0) + 1
        stats["categories"][category] = stats["categories"].get(category, 0) + 1
        
        for i, chunk in enumerate(chunks):
            point_meta = {
                "filename": fname,
                "title": title,
                "source": source,
                "date": date,
                "url": url,
                "doc_type": doc_type,
                "category": category,
                "organization": organization,
                "tags": tags,
                "use_for": use_for,
                "is_fact_safe": is_fact_safe,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "char_count": len(chunk),
                "collection": COLLECTION,
                "ingest_time": datetime.now(TZ_CN).isoformat(),
            }
            
            embedding = embed_model.embed_query(chunk)
            
            all_points.append(PointStruct(
                id=make_point_id(fname, i),
                vector=embedding,
                payload={"text": chunk, "metadata": point_meta}
            ))
    
    # 批量写入 Qdrant（分批 50 条）
    BATCH = 50
    for start in range(0, len(all_points), BATCH):
        batch = all_points[start:start+BATCH]
        client.upsert(collection_name=COLLECTION, points=batch)
        print(f"  写入 {start+len(batch)}/{len(all_points)} points")
    
    print(f"\n✅ Ingest 完成!")
    print(f"  文件数: {stats['total_files']}")
    print(f"  chunk 数: {stats['total_chunks']}")
    print(f"  失败: {stats['failed']}")
    print(f"\n=== doc_type 分布 ===")
    for k, v in sorted(stats['doc_types'].items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\n=== category 分布 ===")
    for k, v in sorted(stats['categories'].items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    
    # 保存 stats
    with open("/tmp/mango_ingest_stats.json", "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
