"""
rag_client.py — 多 collection 风格参考检索客户端

调用 VPS 上已部署的 RAG 系统（localhost:8000）获取风格参考。
支持多 collection 查询、按文种路由、环境变量配置。

只用于 draft 阶段，不得作为事实来源。
如果 RAG 不可用，返回空数组，不阻塞 pipeline。
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

# ─── 环境变量配置 ─────────────────────────────────────────────────────────

RAG_BASE_URL = os.environ.get("RAG_BASE_URL", "http://localhost:8000/search")

# Collection 配置
COLLECTION_STYLE = os.environ.get("RAG_COLLECTION_STYLE", "mango_style_docs")
COLLECTION_BUSINESS = os.environ.get("RAG_COLLECTION_BUSINESS", "jiuyou_docs")
COLLECTION_DISABLED = os.environ.get("RAG_COLLECTION_DISABLED", "openclaw_memory")

# 是否启用多 collection
ENABLE_MULTI_COLLECTION = os.environ.get(
    "RAG_ENABLE_MULTI_COLLECTION", "true"
).lower() == "true"

# 总返回上限
TOP_K_TOTAL = int(os.environ.get("RAG_TOP_K_TOTAL", "6"))

# ─── Metadata Rerank 配置 ────────────────────────────────────────────────

RERANK_ENABLED = os.environ.get("RAG_METADATA_RERANK_ENABLED", "false").lower() == "true"
RERANK_EXPAND_FACTOR = int(os.environ.get("RAG_RERANK_EXPAND_FACTOR", "4"))
RERANK_EXPAND_MIN = int(os.environ.get("RAG_RERANK_EXPAND_MIN", "12"))
RERANK_BONUS_SCALE = float(os.environ.get("RAG_RERANK_BONUS_SCALE", "0.03"))

# 需要 rerank 的 style collection 名称
STYLE_COLLECTIONS = {"mango_style_docs", "mango_style_docs_v020_candidate_rebuild_459"}

# ─── Rerank 权重表 ──────────────────────────────────────────────────────

RERANK_WEIGHTS: Dict[str, Dict[str, float]] = {
    "领导讲话": {
        "source_family:hunan_mango": 2.0,
        "style_weight:high": 1.5,
        "corpus_tier:core": 1.0,
        "doc_type:leader_speech": 1.0,
        "corpus_tier:archive": -2.0,
        "source_family:dianguang_media": -1.0,
    },
    "汇报材料": {
        "source_family:hunan_mango": 1.5,
        "style_weight:high": 1.0,
        "corpus_tier:core": 1.0,
        "corpus_tier:archive": -2.0,
        "source_family:dianguang_media": -0.5,
    },
    "新闻稿": {
        "source_family:dianguang_media": 1.0,
        "source_family:hunan_mango": 0.5,
        "corpus_tier:archive": -1.0,
    },
    "活动稿": {
        "source_family:dianguang_media": 1.0,
        "source_family:hunan_mango": 0.5,
        "corpus_tier:archive": -1.0,
    },
    "司情新闻稿": {
        "source_family:dianguang_media": 1.0,
        "source_family:hunan_mango": 0.5,
        "corpus_tier:archive": -1.0,
    },
    "_default": {
        "style_weight:high": 0.5,
        "corpus_tier:core": 0.5,
        "corpus_tier:archive": -1.0,
    },
}

# 各文种的路由参数
def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))

# ─── 路由规则 ────────────────────────────────────────────────────────────

# 格式: [(collection, top_k), ...]
ROUTING_TABLE: Dict[str, List[tuple]] = {
    # ── 优先使用 mango_style_docs ──
    "新闻稿":      [(COLLECTION_STYLE, _env_int("RAG_NEWS_STYLE_K", 4)),
                    (COLLECTION_BUSINESS, _env_int("RAG_NEWS_BUSINESS_K", 2))],
    "活动稿":      [(COLLECTION_STYLE, 4), (COLLECTION_BUSINESS, 2)],
    "宣传稿":      [(COLLECTION_STYLE, 4), (COLLECTION_BUSINESS, 2)],
    "司情新闻稿":  [(COLLECTION_STYLE, 4), (COLLECTION_BUSINESS, 2)],
    "党建材料":    [(COLLECTION_STYLE, 4), (COLLECTION_BUSINESS, 2)],
    "学习稿":      [(COLLECTION_STYLE, 4), (COLLECTION_BUSINESS, 2)],

    # ── 混合使用 ──
    "领导讲话":    [(COLLECTION_STYLE, _env_int("RAG_SPEECH_STYLE_K", 3)),
                    (COLLECTION_BUSINESS, _env_int("RAG_SPEECH_BUSINESS_K", 3))],
    "通报":        [(COLLECTION_BUSINESS, 5), (COLLECTION_STYLE, 1)],

    # ── 优先使用 jiuyou_docs ──
    "汇报材料":    [(COLLECTION_BUSINESS, _env_int("RAG_REPORT_BUSINESS_K", 5)),
                    (COLLECTION_STYLE, _env_int("RAG_REPORT_STYLE_K", 1))],
    "总结":        [(COLLECTION_BUSINESS, 5), (COLLECTION_STYLE, 1)],
    "报告":        [(COLLECTION_BUSINESS, 6)],
    "请示":        [(COLLECTION_BUSINESS, 6)],
    "通知":        [(COLLECTION_BUSINESS, 6)],
    "函":          [(COLLECTION_BUSINESS, 6)],
    "会议纪要":    [(COLLECTION_BUSINESS, 6)],
}

# 默认路由（未匹配的文种）
DEFAULT_ROUTE = [(COLLECTION_BUSINESS, 4), (COLLECTION_STYLE, 2)]

# ─── 文种 → RAG 查询模板 ────────────────────────────────────────────────

DOC_TYPE_QUERIES: Dict[str, List[str]] = {
    "新闻稿": [
        "芒果系 新闻稿 活动 通稿 标题 开头",
        "广电 芒果 重大活动 新闻稿 传播表达",
    ],
    "活动稿": [
        "芒果系 活动稿 现场报道 活动纪实",
        "广电 芒果 大型活动 活动报道",
    ],
    "宣传稿": [
        "芒果系 宣传稿 品牌宣传 公关稿件",
        "广电 芒果 宣传报道",
    ],
    "司情新闻稿": [
        "芒果系 司情新闻 企业新闻 内部通稿",
        "广电 芒果 公司动态 新闻稿",
    ],
    "领导讲话": [
        "芒果系 领导讲话 站位 判断 部署 要求",
        "广电系统 讲话稿 政治站位 工作部署",
    ],
    "会议纪要": [
        "会议纪要 议定事项 责任分工",
        "广电系统 会议纪要 正式表达",
    ],
    "汇报材料": [
        "芒果系 汇报材料 工作进展 亮点成效",
        "广电系统 专题汇报 经营汇报",
    ],
    "总结": [
        "芒果系 工作总结 阶段总结 成效问题下一步",
        "广电系统 总结材料 正式表达",
    ],
    "报告": [
        "广电系统 工作报告 汇报情况 下一步工作",
        "芒果系 报告 工作成效 存在问题 下一步",
    ],
    "请示": [
        "广电系统 请示 项目支持 上行文",
        "正式公文 请示 妥否请批示",
    ],
    "通知": [
        "正式通知 工作安排 报送材料 时间要求",
        "广电系统 通知 内部材料",
    ],
    "函": [
        "商请函 协助函 平级单位 正式表达",
        "广电系统 函 商洽工作",
    ],
    "通报": [
        "通报 情况通报 工作要求",
        "内部通报 表扬 批评 处理情况",
    ],
    "党建材料": [
        "芒果系 党建 工作报道 党委 学习",
        "广电 党建活动 党纪学习 组织建设",
    ],
    "学习稿": [
        "芒果系 理论学习 中心组 学习心得",
        "广电 学习报道 党建学习",
    ],
}

# 通用查询（未匹配文种时的 fallback）
DEFAULT_QUERY = ["芒果系 公文风格 写作规范 表达方式"]

# ─── do_not_copy 通用规则 ─────────────────────────────────────────────────

DO_NOT_COPY_GENERIC = [
    "具体时间", "具体地点", "领导出席", "领导评价",
    "具体数据", "获奖信息", "项目成果", "人员姓名",
]

RISK_NOTES_GENERIC = [
    "该语料仅用于风格参考，事实必须以 extract_result 为准。",
    "不得将旧稿中的领导出席、领导评价、时间地点当作事实。",
]

# ─── 核心函数 ─────────────────────────────────────────────────────────────


def _query_rag_single(
    query: str,
    collection: str,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """调用 RAG 端点查询单个 collection。"""
    payload = json.dumps({
        "question": query,
        "collection": collection,
        "top_k": top_k,
    }).encode("utf-8")

    req = urllib.request.Request(
        RAG_BASE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("matches", data.get("results", data.get("documents", [])))


def _get_route(doc_type: str) -> List[tuple]:
    """获取文种对应的 collection 路由。"""
    # 测试模式：强制单 collection（A/B 测试用，不影响默认路由）
    force_collection = os.environ.get("RAG_FORCE_COLLECTION", "")
    if force_collection:
        return [(force_collection, TOP_K_TOTAL)]

    if not ENABLE_MULTI_COLLECTION:
        return [(COLLECTION_BUSINESS, TOP_K_TOTAL)]

    return ROUTING_TABLE.get(doc_type, DEFAULT_ROUTE)


def _rerank_snippets(
    snippets: List[Dict[str, Any]],
    doc_type: str,
    original_top_k: int,
    collection: str,
) -> List[Dict[str, Any]]:
    """对 style collection 的检索结果做 metadata-aware rerank。"""
    if not RERANK_ENABLED:
        return snippets[:original_top_k]

    # 只对 style collection 做 rerank
    base_collection = collection.split("/")[0] if "/" in collection else collection
    if base_collection not in STYLE_COLLECTIONS:
        return snippets[:original_top_k]

    weights = RERANK_WEIGHTS.get(doc_type, RERANK_WEIGHTS["_default"])

    reranked = []
    for s in snippets:
        meta = s.get("metadata", {})
        original_score = s.get("score", 0)
        bonus = 0.0

        # source_family
        sf = meta.get("source_family", "")
        bonus += weights.get(f"source_family:{sf}", 0)

        # style_weight
        sw = meta.get("style_weight", "")
        bonus += weights.get(f"style_weight:{sw}", 0)

        # corpus_tier
        ct = meta.get("corpus_tier", "")
        bonus += weights.get(f"corpus_tier:{ct}", 0)

        # doc_type
        dt = meta.get("doc_type", "")
        bonus += weights.get(f"doc_type:{dt}", 0)

        # proposed_doc_subtype（文旅/子公司）
        sub = meta.get("proposed_doc_subtype", "")
        if doc_type in ("活动稿", "宣传稿", "司情新闻稿") and sub in ("culture_tourism", "subsidiary_update"):
            bonus += 1.0

        final_score = original_score + bonus * RERANK_BONUS_SCALE
        s = dict(s)
        s["original_score"] = original_score
        s["metadata_bonus"] = bonus
        s["final_score"] = final_score
        reranked.append(s)

    reranked.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    # 调试日志
    if reranked:
        print(f"[rerank] enabled=true collection={base_collection} doc_type={doc_type}")
        print(f"[rerank] original_top_k={original_top_k} expanded={len(snippets)}")
        for i, s in enumerate(reranked[:original_top_k]):
            m = s.get("metadata", {})
            print(f"[rerank] {i+1}. {m.get('title','')[:35]} | sf={m.get('source_family','?')[:10]} sw={m.get('style_weight','?')} tier={m.get('corpus_tier','?')} | orig={s.get('original_score',0):.3f} bonus={s.get('metadata_bonus',0):.1f} final={s.get('final_score',0):.3f}")

    return reranked[:original_top_k]


def _dedup(snippets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 text_preview 去重，优先保留主 collection。"""
    seen = set()
    result = []
    for s in snippets:
        key = s.get("text", "")[:100]
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result


def _build_style_reference(
    snippets: List[Dict[str, Any]],
    doc_type: str,
    collection_name: str,
) -> Dict[str, Any]:
    """将 snippet 列表组装为一条 style_reference（单 collection）。"""
    if not snippets:
        return {}

    return {
        "source": f"style_rag ({collection_name})",
        "title": snippets[0].get("title", snippets[0].get("metadata", {}).get("title", "")),
        "doc_type": snippets[0].get("metadata", {}).get("doc_type", doc_type),
        "category": snippets[0].get("metadata", {}).get("category", ""),
        "collection": collection_name,
        "use_for": ["标题风格", "开头句式", "段落节奏", "芒果系正式表达"],
        "reference_phrases": [s["text"][:150] for s in snippets[:3]],
        "structure_patterns": [],
        "do_not_copy": DO_NOT_COPY_GENERIC.copy(),
        "risk_notes": RISK_NOTES_GENERIC.copy(),
    }


def retrieve_style_references(
    doc_type: str,
    requirement: str,
    draft: str,
    plan_result: dict,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    获取风格参考（仅用于 draft 阶段）。

    支持多 collection 路由：
    - 新闻稿/活动稿/党建材料：优先 mango_style_docs
    - 领导讲话/通报：混合
    - 公文类（汇报/总结/报告/请示/通知/函/会议纪要）：优先 jiuyou_docs
    - 始终排除 openclaw_memory

    Args:
        doc_type: 文种类型
        requirement: 用户需求
        draft: 用户初稿
        plan_result: plan 阶段输出
        top_k: 单 collection 最大返回数（已废弃，由路由表控制）

    Returns:
        {
            "style_references": [...],
            "rag_status": "success" | "empty" | "failed",
            "rag_count": int,
            "rag_error": str | None,
            "rag_collections_used": [...],
            "rag_primary_collection": str,
            "rag_fallback_collection": str | None,
        }
    """
    route = _get_route(doc_type)
    queries = DOC_TYPE_QUERIES.get(doc_type, DEFAULT_QUERY)

    all_snippets: List[Dict[str, Any]] = []
    collections_used: List[str] = []
    errors: List[str] = []
    actual_queries: List[str] = []

    primary_collection = route[0][0] if route else COLLECTION_BUSINESS
    fallback_collection = route[1][0] if len(route) > 1 else None

    for collection, k in route:
        # 禁止查询 openclaw_memory
        if collection == COLLECTION_DISABLED:
            continue

        # rerank 模式下扩大召回
        effective_k = k
        if RERANK_ENABLED and collection.split("/")[0] in STYLE_COLLECTIONS:
            effective_k = max(RERANK_EXPAND_MIN, k * RERANK_EXPAND_FACTOR)

        for query in queries[:2]:  # 每个文种最多查 2 组 query
            try:
                results = _query_rag_single(query, collection, top_k=effective_k)
                for r in results:
                    if isinstance(r, dict):
                        text = r.get("text", r.get("content", ""))
                        score = r.get("score", r.get("similarity", 0))
                        metadata = r.get("metadata", {})
                        if text and len(text) > 50:
                            all_snippets.append({
                                "text": text[:500],
                                "text_preview": text[:100],
                                "score": score,
                                "query": query,
                                "collection": collection,
                                "title": metadata.get("title", ""),
                                "doc_type": metadata.get("doc_type", ""),
                                "category": metadata.get("category", ""),
                                "source": metadata.get("source", ""),
                                "metadata": metadata,
                            })
                if collection not in collections_used:
                    collections_used.append(collection)
            except Exception as e:
                errors.append(f"RAG 查询失败 ({collection}/{query}): {e}")
            actual_queries.append(f"{collection}:{query}")

    # 去重 + 按 score 降序
    all_snippets = _dedup(all_snippets)
    all_snippets.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 对 style collection 结果做 metadata rerank
    # 分离 style 和 business 结果
    style_snippets = [s for s in all_snippets if s["collection"].split("/")[0] in STYLE_COLLECTIONS]
    business_snippets = [s for s in all_snippets if s["collection"].split("/")[0] not in STYLE_COLLECTIONS]

    if RERANK_ENABLED and style_snippets:
        # 找到 style collection 的原始 top_k
        style_top_k = 3  # 默认
        for coll, k in route:
            if coll.split("/")[0] in STYLE_COLLECTIONS:
                style_top_k = k
                break
        style_snippets = _rerank_snippets(style_snippets, doc_type, style_top_k, style_snippets[0]["collection"] if style_snippets else "")

    # 合并 style + business，按 final_score 降序
    all_snippets = style_snippets + business_snippets
    all_snippets.sort(key=lambda x: x.get("final_score", x.get("score", 0)), reverse=True)

    # 限制总数
    final_snippets = all_snippets[:TOP_K_TOTAL]

    # 错误处理
    if errors and not final_snippets:
        return {
            "style_references": [],
            "rag_status": "failed",
            "rag_count": 0,
            "rag_error": "; ".join(errors),
            "rag_collections_used": [],
            "rag_primary_collection": primary_collection,
            "rag_fallback_collection": fallback_collection,
            "rag_query": " | ".join(actual_queries),
            "rag_sources": [],
        }

    if not final_snippets:
        return {
            "style_references": [],
            "rag_status": "empty",
            "rag_count": 0,
            "rag_error": None,
            "rag_collections_used": collections_used if collections_used else [primary_collection],
            "rag_primary_collection": primary_collection,
            "rag_fallback_collection": fallback_collection,
            "rag_query": " | ".join(actual_queries),
            "rag_sources": [],
        }

    # 按 collection 分组，每组生成一条 style_reference
    grouped: Dict[str, List[Dict]] = {}
    for s in final_snippets:
        coll = s["collection"]
        grouped.setdefault(coll, []).append(s)

    style_references = []
    for coll, snippets in grouped.items():
        ref = _build_style_reference(snippets, doc_type, coll)
        if ref:
            ref["reference_phrases"] = [s["text"][:150] for s in snippets[:3]]
            ref["score_avg"] = sum(s.get("score", 0) for s in snippets) / len(snippets)
            style_references.append(ref)

    return {
        "style_references": style_references,
        "rag_status": "success",
        "rag_count": len(final_snippets),
        "rag_error": None,
        "rag_collections_used": collections_used,
        "rag_primary_collection": primary_collection,
        "rag_fallback_collection": fallback_collection,
        "rag_query": " | ".join(actual_queries),
        "rag_sources": [s["query"] for s in final_snippets[:5]],
    }
