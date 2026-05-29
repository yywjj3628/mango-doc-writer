#!/usr/bin/env bash
# run_regression.sh — 全量回归测试
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

# ─── 预检查 ───
echo "🔍 Running check_env..."
if ! python3 deploy/check_env.py; then
    echo "❌ 环境检查失败，终止运行"
    exit 1
fi

echo "🔍 Running healthcheck..."
if ! python3 deploy/healthcheck.py; then
    echo "⚠️  健康检查有警告，继续运行"
fi

# ─── 收集所有 case 文件 ───
CASES_DIR="tests/cases"
CASES=()
if [ -d "$CASES_DIR" ]; then
    while IFS= read -r -d '' f; do
        CASES+=("$f")
    done < <(find "$CASES_DIR" -name "*.md" -print0 | sort -z)
fi

if [ ${#CASES[@]} -eq 0 ]; then
    echo "❌ 未找到测试用例: $CASES_DIR/*.md"
    exit 1
fi

echo "🚀 Running ${#CASES[@]} cases..."
PASSED=0
FAILED=0

for CASE in "${CASES[@]}"; do
    echo ""
    echo "════════════════════════════════════════════"
    echo "📄 $(basename "$CASE")"
    echo "════════════════════════════════════════════"
    if python3 scripts/run_case.py "$CASE"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
        echo "❌ FAILED: $(basename "$CASE")"
    fi
done

echo ""
echo "════════════════════════════════════════════"
echo "📊 结果: $PASSED passed, $FAILED failed, ${#CASES[@]} total"
echo "════════════════════════════════════════════"

[ $FAILED -eq 0 ]
