#!/usr/bin/env bash
# run_single.sh — 运行单篇测试
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ─── 环境变量加载（优先级：/etc > 项目 .env） ───
if [ -f /etc/mango-doc-writer.env ]; then
    set -a; . /etc/mango-doc-writer.env; set +a
elif [ -f .env ]; then
    set -a; . .env; set +a
fi

# ─── 参数检查 ───
CASE_FILE="${1:?用法: bash deploy/run_single.sh <case_file>}"
if [ ! -f "$CASE_FILE" ]; then
    echo "❌ 文件不存在: $CASE_FILE"
    exit 1
fi

# ─── 预检查 ───
echo "🔍 Running check_env..."
if ! python3 deploy/check_env.py; then
    echo "❌ 环境检查失败，终止运行"
    exit 1
fi

# ─── 运行 ───
echo "🚀 Running: $CASE_FILE"
python3 scripts/run_case.py "$CASE_FILE"
