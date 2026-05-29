# mango-doc-writer 回归测试

## 为什么需要回归测试

六阶段 Prompt 管线（classify → extract → plan → draft → review → rewrite）经过 12.5A 手动验证后已证明核心逻辑正确。但随着后续迭代（Prompt 优化、Schema 扩展、新 case 增加），任何修改都可能导致已有验证通过的 case 退化。

回归测试的目标：

- **防止退化**：每次修改后一键验证所有 case 仍然通过
- **快速定位**：哪个阶段、哪项检查出了问题
- **最小成本**：不接 API、不接 typeset-engine，纯本地轻量脚本

## 局限性说明

**Schema 校验只能检查结构，不能检查事实真实性。**

- JSON schema 验证的是"格式是否正确"（字段类型、必填项、枚举值）
- 但无法验证"内容是否正确"（如 draft 是否编造了事实、final_markdown 是否包含 RAG 污染）
- 因此需要 watchlist 词表扫描 + per-case 特殊规则来补充

## watchlist 的作用

`watchlist.yaml` 包含三类观察词：

| 词类 | 用途 | 示例 |
|------|------|------|
| unsupported_claims | 无依据拔高表达 | "取得重大突破""产生广泛影响" |
| leadership_claims | 领导评价/出席风险 | "领导高度肯定""领导莅临" |
| doc_type_conflicts | 文种冲突表达 | 报告中出现"请批准"、请示中出现"特此报告" |

观察词覆盖面有限，但覆盖了 12.5A 验证中暴露的高频风险模式。

## review 硬规则检查（阶段 12.7 新增）

`check_report.py` 会自动检查 review_result 的 critical issue 联动约束：

1. 存在 critical issue → rewrite_required 必须为 true
2. 存在 critical issue → pass 必须为 false
3. 存在 critical issue → rewrite_instructions 不得为空
4. 存在 critical issue → risk_level 应为 critical 或 high

违反任一约束将导致该 case 回归测试失败。

## 如何运行

### 运行全部回归检查

```bash
cd skills/mango-doc-writer
python tests/regression/run_regression.py
```

默认检查 002-fake-report-real-request 和 009-rag-pollution 两个 case。

### 指定 case

```bash
python tests/regression/run_regression.py --cases 002-fake-report-real-request 009-rag-pollution 003-report
```

### 运行单个 case 的 report 检查

```bash
python tests/regression/check_report.py tests/reports/002-fake-report-real-request
```

### 运行单个 case 的 markdown claims 检查

```bash
python tests/regression/check_markdown_claims.py tests/reports/009-rag-pollution/rewrite_result.json --case-id 009-rag-pollution
```

也可以直接传入 .md 文件：

```bash
python tests/regression/check_markdown_claims.py tests/reports/002/final_markdown.md --case-id 002-fake-report-real-request
```

## 如何解读 regression-summary.json

```json
{
  "total_cases": 2,
  "passed": 2,
  "failed": 0,
  "cases": [
    {
      "case_id": "002-fake-report-real-request",
      "pass": true,
      "checks": {
        "report": true,
        "markdown_claims": true
      }
    }
  ]
}
```

- `pass`：该 case 两个检查均通过
- `checks.report`：六阶段 JSON 完整性 + schema + 策略合规
- `checks.markdown_claims`：final_markdown 无观察词命中 + per-case 特殊规则通过

## 后续如何扩展

1. **增加新 case**：在 `run_regression.py` 的 `DEFAULT_CASES` 中添加 case_id
2. **增加观察词**：在 `watchlist.yaml` 中追加
3. **增加 per-case 规则**：在 `check_markdown_claims.py` 的 `CASE_RULES` 中添加
4. **扩展到 10 个 case**：完成剩余 8 个 case 的手动验证后，将报告 JSON 放入对应目录即可

## 纪律要求

1. **不得为了通过回归测试修改输出报告**（tests/reports/stage-12-5A-validation-report.md 不可修改）
2. **不得为了通过回归测试修改 watchlist**（减少观察词 = 降低标准）
3. **发现失败时应回到 Prompt 或规则层分析原因**
4. **修改 prompts / schemas / references 后必须运行回归测试**

## 依赖

- Python 3.10+
- PyYAML (`pip install pyyaml`)
- jsonschema (`pip install jsonschema`)
