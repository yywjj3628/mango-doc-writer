# mango-doc-writer 开发者手册

## 六阶段流程 + 质量门禁

```
用户初稿 → 01-classify → 02-extract → 03-plan → 04-draft → 05-review → 06-rewrite → final_markdown
                                                                                          ↓
                                                                              [quality gate 后置门禁]
                                                                                          ↓
                                                                                  final_markdown（主输出）
```

**注意：quality gate 不是第七阶段。** 六阶段 STAGES 不变：classify → extract → plan → draft → review → rewrite。quality gate 是 rewrite 后的后置评估函数，通过环境变量 `QUALITY_GATE_ENABLED` 控制开关。

### 01-classify（文种识别）

**输入**：用户初稿 + 需求描述
**输出**：doc_type、direction、style_level、risk_level、conflict_detected

- 识别文种（新闻稿/通知/请示/报告/函/总结/汇报材料/领导讲话/会议纪要/通报）
- 检测文种冲突（如素材说"报告"但内容像请示）
- 输出 classify_result.json

### 02-extract（事实抽取）

**输入**：用户初稿 + classify_result
**输出**：facts、fact_items、missing_fields、cannot_infer、risk_flags

- 只抽取用户明确提供的事实
- 不补充、不推测、不编造
- 标记缺失字段和不可推断内容
- 输出 extract_result.json

### 03-plan（结构规划）

**输入**：classify_result + extract_result
**输出**：sections、title_plan、manual_confirmation_fields、draft_directives

- 规划文案结构（不生成正文）
- 绑定每个 section 的事实来源
- 标记 blocked_items（禁止写入的内容）
- 输出 plan_result.json

### 04-draft（初稿生成）

**输入**：classify_result + extract_result + plan_result
**输出**：markdown_draft、fact_usage_report、rag_usage_report

- 第一次允许生成正文
- 第一次允许使用 style_rag（仅风格参考）
- RAG 只用于风格，不作为事实来源
- 输出 draft_result.json

### 05-review（质检）

**输入**：draft_result + classify_result + extract_result + plan_result
**输出**：pass、score、issues、rewrite_instructions

- 不生成正文，不改写正文
- 检查事实溯源、文种规则、称谓口径、RAG 使用
- 输出 review_result.json
- **硬规则**：存在 critical issue 时 rewrite_required 必须为 true

### 06-rewrite（二次修订）

**输入**：draft_result + review_result + extract_result
**输出**：final_markdown、revision_report、rewrite_policy

- 根据 review_result.issues 逐项修订
- 不调用 RAG，不新增事实
- 输出 rewrite_result.json

## Schema 作用

| Schema | 作用 |
|--------|------|
| classify.schema.json | 规范 classify 输出格式 |
| extract.schema.json | 规范 extract 输出格式（含 extraction_policy） |
| plan.schema.json | 规范 plan 输出格式 |
| draft.schema.json | 规范 draft 输出格式（含 draft_policy） |
| review.schema.json | 规范 review 输出格式（含 review_policy） |
| rewrite.schema.json | 规范 rewrite 输出格式（含 rewrite_policy） |
| quality_score.schema.json | 规范质量门禁输出格式（六大维度评分 + 门禁决策） |

## Prompt 作用

| Prompt | 作用 |
|--------|------|
| 01-classify.md | 文种识别规则、冲突检测逻辑 |
| 02-extract.md | 事实抽取规则、不得补充原则 |
| 03-plan.md | 结构规划规则、blocked_items |
| 04-draft.md | 正文生成规则、RAG 使用边界 |
| 05-review.md | 质检规则、critical issue 硬规则 |
| 06-rewrite.md | 修订规则、rewrite_policy |
| 07-quality-score.md | 质量门禁评分规则、六维度评分标准、返修指令生成 |

## 如何跑单个 case

```bash
cd skills/mango-doc-writer

# 排版输出
python scripts/render_case.py tests/reports/002-fake-report-real-request
```

## 如何跑回归测试

```bash
# 全量回归（10 个 case）
python tests/regression/run_regression.py

# 单 case 检查
python tests/regression/check_report.py tests/reports/002-fake-report-real-request
python tests/regression/check_markdown_claims.py tests/reports/002/rewrite_result.json --case-id 002-fake-report-real-request
```

## 排查 schema_validation_error

1. 确认 JSON 文件存在且非空
2. 用 `json.load` 验证 JSON 格式
3. 用 `jsonschema.validate` 对照 schemas/*.json 校验
4. 检查 const:true 字段（extraction_policy/draft_policy/review_policy/rewrite_policy）
5. 检查 required 字段是否缺失

## 排查 RAG 污染

1. 检查 draft_result.rag_usage_report 是否有 fact_risk=true
2. 检查 review_result.issues 是否有 type=rag_fact_pollution
3. 检查 final_markdown 是否包含用户未提供的事实
4. 对照 watchlist.yaml 的 unsupported_claims 和 leadership_claims

## 排查称谓错误

1. 检查 extract_result.missing_fields 是否有机构/领导相关字段
2. 检查 draft_result.terminology_usage_report 是否有 needs_manual_confirmation=true
3. 对照 references/org-title-dictionary.yaml

## 接入 API 自动化

当前状态：未接入
建议方案：
1. 用 Python 脚本调用智谱 API（GLM-5-Turbo）
2. 每个阶段的 Prompt 作为 system message
3. 前阶段输出作为 user message 传入后阶段
4. 用 jsonschema.validate 校验输出

## 接入 typeset-engine

已接入。render_pipeline.py 调用 localhost:9090 HTTP API。

```bash
python scripts/render_case.py tests/reports/<case_id> --format docx
```

## 质量门禁维护指南（v0.1.3 新增）

### prompts/07-quality-score.md

职责：定义质量门禁的评分规则、六维度评分标准、返修指令生成规则。

- 六个评分维度：fact_safety / doc_type_fit / mango_style_fit / logic_completeness / language_quality / risk_control
- 每个维度 0-10 分，阈值默认 8
- 低于阈值时生成 quality_rewrite_instructions
- 不生成正文、不修改正文、不调用 RAG

### schemas/quality_score.schema.json

职责：规范质量门禁输出的 JSON 格式。

关键枚举字段：

| 字段 | 枚举值 |
|------|--------|
| no_new_facts_check.status | pass / warning / fail |
| doc_type_check.status | pass / warning / fail |
| style_check.status | pass / warning / fail |
| final_output_policy.recommendation | pass / rewrite / warn_and_output |
| quality_rewrite_instructions[].suggested_action | delete / replace / restructure |
| failed_dimensions[] | fact_safety / doc_type_fit / mango_style_fit / logic_completeness / language_quality / risk_control |

**重要**：Prompt 中的 JSON 示例枚举值必须与 Schema 定义完全一致。

### pipeline/run_pipeline.py 中的 quality gate 循环

```python
# 环境变量
QUALITY_GATE_ENABLED=true   # 开关
QUALITY_GATE_THRESHOLD=8    # 阈值
QUALITY_GATE_MAX_ROUNDS=2   # 最大返修轮次

# 循环逻辑（简化）
while True:
    qg_result = run_stage("quality_score", ...)
    if qg_result.overall_pass:
        # 通过，输出 final_markdown
        break
    if round >= max_rounds:
        # 达到最大轮次，warn_and_output
        break
    # 返修：将 instructions 交给 rewrite
    rewrite_result = run_stage("rewrite", ... + instructions)
    final_markdown = rewrite_result.final_markdown
```

### pipeline_report 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| quality_gate_enabled | bool | 质量门禁是否启用 |
| quality_gate_pass | bool/None | 最终是否通过 |
| quality_gate_threshold | float | 阈值 |
| quality_gate_rounds_used | int | 实际使用轮次 |
| quality_gate_max_rounds | int | 最大轮次 |
| final_quality_scores | dict | 六维度最终评分 |
| quality_score_history | list | 每轮评分记录 |
| quality_gate_error | str/None | 错误信息 |
| quality_rewrite_applied | bool | 是否有返修 |

### 如何调试 quality gate

1. 检查 pipeline_report.json 中的 quality_gate_* 字段
2. 查看 quality_score_history 了解每轮评分变化
3. 用 schema 校验 quality_score 输出：`validate_result('quality_score', data)`
4. 检查 quality_rewrite_instructions 是否合理
5. 检查 final_output_policy.recommendation 是否符合预期

### 如何关闭 quality gate

```bash
export QUALITY_GATE_ENABLED=false
```

关闭后完全回到 v0.1.2 旧流程，rewrite 输出直接作为最终结果。

### 如何调整阈值和最大返修轮次

```bash
export QUALITY_GATE_THRESHOLD=7    # 降低阈值（默认 8）
export QUALITY_GATE_MAX_ROUNDS=3   # 增加返修轮次（默认 2）
```

### Schema 校验失败排查

1. 确认 quality_score 输出 JSON 格式正确
2. 检查枚举值是否在 Schema 定义范围内（特别是 status、recommendation、suggested_action）
3. 检查 required 字段是否缺失
4. 检查 quality_gate_policy 六项是否全部为 true
5. 对照 prompts/07-quality-score.md 中的示例 JSON

### review.score 与 quality_score 的区别

| 维度 | review.score | quality_score |
|------|-------------|---------------|
| 评估对象 | draft_result（初稿） | final_markdown（成稿） |
| 执行阶段 | 五阶段（review） | 后置门禁（rewrite 之后） |
| 调用 RAG | 不调用 | 不调用 |
| 返回修改 | 给 rewrite 指令 | 给 rewrite 指令 |
| 目的 | 初稿合规性 | 成稿交付质量 |
| 分数范围 | 0-100 | 0-10（六维度） |
| 通过条件 | score >= 阈值 且无 critical issue | 所有维度 >= 阈值 |

## 哪些文件不能随便改

| 文件 | 原因 |
|------|------|
| prompts/*.md | 改动会影响六阶段输出质量 |
| schemas/*.json | 改动会导致已有输出不兼容 |
| references/*.md/yaml | 改动会影响规则和称谓判断 |
| tests/cases/*.md | 改动会导致回归测试失效 |
| tests/reports/*/rewrite_result.json | 改动会影响回归测试结果 |
| tests/fixtures/quality_score_*.json | 改动会导致质量门禁测试失效 |
