#!/usr/bin/env python3
"""
healthcheck.py — 运行时轻量健康检查

检查各服务可达性和目录状态，不跑完整回归、不消耗 API token。

用法:
  python deploy/healthcheck.py
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check_deepseek():
    """检查 DeepSeek API 配置（不实际调用模型）"""
    key = os.environ.get("DEEPSEEK_API_KEY")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    if not key or key == "replace_with_your_key":
        return "unavailable", "DEEPSEEK_API_KEY 未设置"

    # 可选：极轻量 API 测试（仅验证 key 有效）
    try:
        import requests
        # 使用 models 列表接口验证 key，不消耗 token
        headers = {"Authorization": f"Bearer {key}"}
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=5)
        if resp.status_code == 200:
            return "ok", f"model={model}, base_url={base_url}"
        elif resp.status_code == 401:
            return "unavailable", "API key 无效"
        else:
            return "warning", f"API 返回状态码 {resp.status_code}"
    except Exception as e:
        return "warning", f"无法验证: {e}"


def check_rag():
    """检查 RAG 服务可达性和 collection 状态"""
    rag_enabled = os.environ.get("RAG_ENABLED", "true").lower() == "true"
    if not rag_enabled:
        return "disabled", "RAG 未启用"

    rag_url = os.environ.get("RAG_BASE_URL", "http://localhost:8000")
    try:
        import requests
        resp = requests.get(f"{rag_url}/health", timeout=3)
        if resp.status_code == 200:
            return "ok", f"{rag_url}"
        return "warning", f"RAG 返回 {resp.status_code}"
    except Exception as e:
        return "unavailable", str(e)


def check_rag_collections():
    """检查 RAG collection 可用性"""
    rag_enabled = os.environ.get("RAG_ENABLED", "true").lower() == "true"
    if not rag_enabled:
        return {"status": "disabled", "detail": "RAG 未启用"}

    import requests
    collections = [
        ("mango_style_docs", os.environ.get("RAG_COLLECTION_STYLE", "mango_style_docs")),
        ("jiuyou_docs", os.environ.get("RAG_COLLECTION_BUSINESS", "jiuyou_docs")),
    ]
    result = {}
    all_ok = True
    for name, coll in collections:
        try:
            resp = requests.get("http://localhost:6333/collections/" + coll, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                points = data.get("result", {}).get("points_count", 0)
                status = data.get("result", {}).get("status", "unknown")
                result[coll] = {"status": status, "points": points}
            else:
                result[coll] = {"status": "error", "points": 0}
                all_ok = False
        except Exception as e:
            result[coll] = {"status": "unavailable", "points": 0}
            all_ok = False

    return {"status": "ok" if all_ok else "warning", "collections": result}


def check_typeset_engine():
    """检查 typeset-engine 可达性"""
    te_enabled = os.environ.get("TYPESET_ENGINE_ENABLED", "true").lower() == "true"
    if not te_enabled:
        return "disabled", "typeset-engine 未启用"

    te_url = os.environ.get("TYPESET_ENGINE_BASE_URL", "http://localhost:9090")
    try:
        import requests
        resp = requests.get(f"{te_url}/health", timeout=3)
        if resp.status_code == 200:
            return "ok", f"{te_url}"
        return "warning", f"返回 {resp.status_code}"
    except Exception as e:
        return "warning", str(e)


def check_writable_dirs():
    """检查输出目录可写"""
    dirs = {
        "reports": PROJECT_ROOT / "tests" / "reports",
        "outputs": PROJECT_ROOT / "outputs",
        "logs": PROJECT_ROOT / "logs",
    }
    result = {}
    for name, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        result[name] = os.access(str(path), os.W_OK)
    return result


def run():
    deepseek_status, deepseek_detail = check_deepseek()
    rag_status, rag_detail = check_rag()
    rag_collections = check_rag_collections()
    te_status, te_detail = check_typeset_engine()
    writable = check_writable_dirs()

    # 确定总体状态
    statuses = [deepseek_status, rag_status, te_status]
    if deepseek_status == "unavailable":
        overall = "failed"
    elif any(s in ("warning", "unavailable") for s in statuses):
        overall = "warning"
    else:
        overall = "ok"

    result = {
        "status": overall,
        "deepseek": {"status": deepseek_status, "detail": deepseek_detail},
        "rag": {"status": rag_status, "detail": rag_detail, "collections": rag_collections},
        "typeset_engine": {"status": te_status, "detail": te_detail},
        "reports_writable": writable.get("reports", False),
        "outputs_writable": writable.get("outputs", False),
        "logs_writable": writable.get("logs", False),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    icon = {"ok": "✅", "warning": "⚠️", "failed": "❌"}.get(overall, "?")
    print(f"\n{icon} 总体状态: {overall}")
    return 0 if overall != "failed" else 1


if __name__ == "__main__":
    sys.exit(run())
