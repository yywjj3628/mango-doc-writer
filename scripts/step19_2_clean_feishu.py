#!/usr/bin/env python3
"""
Step 19.2 — 从飞书拉取的数据清洗为标准 Markdown（带 YAML front matter）。
输入: /tmp/feishu_clean.json (60 条飞书 bitable 记录)
输出: corpus/mango_style_docs/cleaned/*.md + corpus/mango_style_docs/manifest.yaml
"""
import json, os, sys, re, yaml
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEANED_DIR = os.path.join(BASE, "corpus", "mango_style_docs", "cleaned")
MANIFEST_PATH = os.path.join(BASE, "corpus", "mango_style_docs", "manifest.yaml")
RAW_PATH = "/tmp/feishu_clean.json"

TZ_CN = timezone(timedelta(hours=8))

def extract_text(field):
    """从飞书 rich text 或普通字段提取纯文本"""
    if field is None:
        return ""
    if isinstance(field, list):
        return "".join(part.get("text", "") for part in field if isinstance(part, dict))
    if isinstance(field, str):
        return field
    return str(field)

def extract_url(field):
    if field is None:
        return ""
    if isinstance(field, dict) and field.get("link"):
        return field["link"]
    return ""

def classify_doc_type(title, source):
    t = title
    if any(w in t for w in ["党委", "理论学习", "研讨", "政绩观", "读书班"]):
        return "领导讲话"
    if any(w in t for w in ["纪法", "讲堂", "纪检培训"]):
        return "通报"
    if any(w in t for w in ["AI", "人工智能", "拥抱AI", "驾驭AI"]):
        return "领导讲话"
    if any(w in t for w in ["青春π对", "青年座谈"]):
        return "活动稿"
    if any(w in t for w in ["党风廉政", "纪检监察", "廉洁"]):
        return "党建材料"
    return "新闻稿"

def classify_category(title):
    t = title
    if any(w in t for w in ["文旅", "星光行动", "开街", "开业", "旅游", "旅发"]):
        return "产业合作"
    if any(w in t for w in ["超高清", "4K"]):
        return "文化科技融合"
    if any(w in t for w in ["AI", "人工智能", "拥抱AI", "驾驭AI"]):
        return "文化科技融合"
    if any(w in t for w in ["党委", "理论学习", "研讨", "政绩观", "党建", "纪法"]):
        return "党建材料"
    if any(w in t for w in ["联赛", "赛事", "比赛"]):
        return "活动稿"
    if any(w in t for w in ["合作", "签约", "备忘录"]):
        return "产业合作"
    return "活动稿"

def infer_tags(title):
    tags = ["湖南广电", "芒果"]
    if any(w in title for w in ["文旅", "旅游", "旅发", "星光"]):
        tags.append("文旅")
    if any(w in title for w in ["AI", "人工智能", "科技", "4K", "超高清"]):
        tags.append("文化科技融合")
    if any(w in title for w in ["党建", "纪检", "廉洁", "纪法"]):
        tags.append("党建纪检")
    if any(w in title for w in ["青春", "青年"]):
        tags.append("青年")
    if any(w in title for w in ["电广传媒"]):
        tags.append("电广传媒")
    return tags

def safe_filename(title, idx):
    """生成安全文件名"""
    # 取标题前30字符 + 索引
    name = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)[:40].strip('_')
    if not name:
        name = f"article_{idx}"
    return f"{name}.md"

def main():
    os.makedirs(CLEANED_DIR, exist_ok=True)
    
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    manifest_docs = []
    success = 0
    failed = 0
    
    for idx, item in enumerate(items):
        fields = item.get("fields", {})
        body_raw = fields.get("正文")
        if body_raw is None:
            continue
        
        title = extract_text(fields.get("标题", ""))
        source = extract_text(fields.get("来源", ""))
        time_ts = fields.get("时间")
        url = extract_url(fields.get("链接"))
        body = extract_text(body_raw)
        
        if not title.strip() or not body.strip():
            failed += 1
            continue
        
        # 解析日期
        if time_ts:
            try:
                dt = datetime.fromtimestamp(time_ts / 1000, tz=TZ_CN)
                date_str = dt.strftime("%Y-%m-%d")
            except:
                date_str = ""
        else:
            date_str = ""
        
        doc_type = classify_doc_type(title, source)
        category = classify_category(title)
        tags = infer_tags(title)
        
        # use_for 推断
        use_for = ["style", "opening", "rhythm"]
        if doc_type == "领导讲话":
            use_for.append("title")
            use_for.append("structure")
        
        # 构造 front matter
        front = {
            "title": title.strip(),
            "source": source.strip(),
            "date": date_str,
            "url": url,
            "doc_type": doc_type,
            "category": category,
            "organization": "湖南广电集团",
            "tags": tags,
            "use_for": use_for,
            "is_fact_safe": False,
        }
        
        # 清洗正文
        # 移除开头的来源标记（如 "（感谢xxx供稿！）"）
        body = re.sub(r'（感谢.*?供稿[！）]）', '', body)
        body = re.sub(r'\n{3,}', '\n\n', body)
        body = body.strip()
        
        # 写入 Markdown
        fname = safe_filename(title, idx)
        filepath = os.path.join(CLEANED_DIR, fname)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.dump(front, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            f.write("\n---\n\n")
            f.write(body + "\n")
        
        success += 1
        manifest_docs.append({
            "file": fname,
            "title": title.strip(),
            "doc_type": doc_type,
            "category": category,
            "source": source.strip(),
            "date": date_str,
            "url": url,
            "char_count": len(body),
            "status": "ready",
        })
    
    # 写 manifest
    manifest = {
        "version": "0.1",
        "collection": "mango_style_docs",
        "description": "芒果系文案风格语料库，仅用于 style_rag",
        "created_at": datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M"),
        "updated_at": datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M"),
        "fact_policy": "style_only_not_fact_source",
        "documents": manifest_docs,
    }
    
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    # 统计
    doc_types = {}
    categories = {}
    for doc in manifest_docs:
        dt = doc["doc_type"]
        cat = doc["category"]
        doc_types[dt] = doc_types.get(dt, 0) + 1
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"✅ 清洗完成: {success} 篇成功, {failed} 篇失败")
    print(f"\n=== doc_type 分布 ===")
    for k, v in sorted(doc_types.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\n=== category 分布 ===")
    for k, v in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\n输出: {CLEANED_DIR}/ ({len(os.listdir(CLEANED_DIR))} files)")
    print(f"Manifest: {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
