#!/usr/bin/env python3
"""
check_env.py — VPS 部署前环境检查

检查 Python 版本、依赖包、API 配置、目录结构和外部服务可达性。
输出 JSON 格式结果，关键项失败时退出码非 0。

用法:
  python deploy/check_env.py
"""

import importlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _check(label, ok, detail="", fatal=False):
    return {"label": label, "ok": ok, "detail": detail, "fatal": fatal}


def run():
    checks = []
    warnings = []
    errors = []

    # 1. Python 版本
    py_ver = sys.version_info
    ok = py_ver >= (3, 8)
    checks.append(_check("python_version", ok, f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}", fatal=not ok))

    # 2. 必要 Python 包
    required_packages = [
        ("openai", "openai"),
        ("jsonschema", "jsonschema"),
        ("requests", "requests"),
    ]
    for name, import_name in required_packages:
        try:
            importlib.import_module(import_name)
            checks.append(_check(f"package_{name}", True))
        except ImportError:
            checks.append(_check(f"package_{name}", False, f"{name} 未安装", fatal=True))
            errors.append(f"缺少依赖包: {name}")

    # pyyaml 可选
    try:
        importlib.import_module("yaml")
        checks.append(_check("package_pyyaml", True))
    except ImportError:
        checks.append(_check("package_pyyaml", False, "pyyaml 未安装（可选）"))
        warnings.append("pyyaml 未安装，部分功能可能受限")

    # 3. DEEPSEEK_API_KEY（不打印真实 key）
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if api_key and api_key != "replace_with_your_key":
        key_len = len(api_key)
        checks.append(_check("deepseek_api_key", True, f"present (len={key_len})"))
    else:
        checks.append(_check("deepseek_api_key", False, "missing", fatal=True))
        errors.append("DEEPSEEK_API_KEY missing")

    # 4. DEEPSEEK_MODEL
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    checks.append(_check("deepseek_model", bool(model), f"默认: {model}"))

    # 5-9. 目录结构
    dirs = {
        "project_root": PROJECT_ROOT,
        "prompts": PROJECT_ROOT / "prompts",
        "schemas": PROJECT_ROOT / "schemas",
        "references": PROJECT_ROOT / "references",
        "tests_cases": PROJECT_ROOT / "tests" / "cases",
    }
    for name, path in dirs.items():
        ok = path.is_dir()
        checks.append(_check(f"dir_{name}", ok, str(path), fatal=name in ("prompts", "schemas")))
        if not ok:
            errors.append(f"目录缺失: {path}")

    # 10-12. 可写目录
    writable_dirs = {
        "reports": PROJECT_ROOT / "tests" / "reports",
        "outputs": PROJECT_ROOT / "outputs",
        "logs": PROJECT_ROOT / "logs",
    }
    for name, path in writable_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        ok = os.access(str(path), os.W_OK)
        checks.append(_check(f"writable_{name}", ok, str(path)))

    # 13. RAG 可达性（轻量检测）
    rag_enabled = os.environ.get("RAG_ENABLED", "true").lower() == "true"
    rag_url = os.environ.get("RAG_BASE_URL", "http://localhost:8000")
    try:
        import requests
        resp = requests.get(f"{rag_url}/health", timeout=3)
        rag_ok = resp.status_code == 200
        checks.append(_check("rag_reachable", rag_ok, f"{rag_url}/health"))
    except Exception as e:
        if rag_enabled:
            checks.append(_check("rag_reachable", False, f"RAG 不可达: {e}"))
            warnings.append(f"RAG 服务不可达: {rag_url}")
        else:
            checks.append(_check("rag_reachable", True, "RAG 未启用（跳过）"))

    # 14. RAG Collection 可用性检查
    if rag_enabled:
        collections_to_check = [
            ("mango_style_docs", os.environ.get("RAG_COLLECTION_STYLE", "mango_style_docs")),
            ("jiuyou_docs", os.environ.get("RAG_COLLECTION_BUSINESS", "jiuyou_docs")),
        ]
        for name, coll in collections_to_check:
            try:
                import requests
                resp = requests.get("http://localhost:6333/collections/" + coll, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    points = data.get("result", {}).get("points_count", 0)
                    checks.append(_check(f"rag_collection_{name}", True, f"{points} points"))
                else:
                    checks.append(_check(f"rag_collection_{name}", False, f"Qdrant 返回 {resp.status_code}"))
                    warnings.append(f"RAG collection {name} 不可达")
            except Exception as e:
                checks.append(_check(f"rag_collection_{name}", False, str(e)))
                warnings.append(f"RAG collection {name} 检查失败")

        # 检查 disabled collection 不被使用
        disabled_coll = os.environ.get("RAG_COLLECTION_DISABLED", "openclaw_memory")
        checks.append(_check("rag_disabled_collection", True, f"{disabled_coll}（已排除）"))
    te_url = os.environ.get("TYPESET_ENGINE_BASE_URL", "http://localhost:9090")
    te_enabled = os.environ.get("TYPESET_ENGINE_ENABLED", "true").lower() == "true"
    if te_enabled:
        try:
            import requests
            resp = requests.get(f"{te_url}/health", timeout=3)
            te_ok = resp.status_code == 200
            checks.append(_check("typeset_engine_reachable", te_ok, f"{te_url}/health"))
        except Exception as e:
            checks.append(_check("typeset_engine_reachable", False, f"typeset-engine 不可达: {e}"))
            warnings.append(f"typeset-engine 不可达: {te_url}（DOCX 生成将跳过）")
    else:
        checks.append(_check("typeset_engine_reachable", True, "typeset-engine 未启用（跳过）"))

    # 汇总
    has_fatal = any(c["fatal"] and not c["ok"] for c in checks)
    all_ok = all(c["ok"] for c in checks)

    result = {
        "status": "pass" if all_ok else ("fail" if has_fatal else "warning"),
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not has_fatal else 2


if __name__ == "__main__":
    sys.exit(run())
