# 阶段 1 执行报告：质量门禁 Prompt + Schema 设计

> **执行时间**：2026-05-29 06:50 UTC
> **执行内容**：设计 quality gate 的 Prompt 和 Schema 契约，轻量增强 rewrite prompt
> **不涉及**：Pipeline 执行逻辑接入（留待阶段 2）

---

## 1. 新增/修改文件清单

| 操作 | 文件 | 大小 | 说明 |
|------|------|------|------|
| **新增** | `prompts/07-quality-score.md` | ~13.9 KB | 质量门禁 Prompt，含六大维度评分规则、三个完整示例 |
| **新增** | `schemas/quality_score.schema.json` | ~9.7 KB | 质量门禁输出 Schema，16 个 required 字段 |
| **修改** | `prompts/06-rewrite.md` | 新增 ~40 行 | 新增"质量门禁返修模式"章节 + quality_rewrite_instructions 输入变量 |
| 未修改 | `schemas/rewrite.schema.json` | — | 经评估，**不需要修改**（理由见第 5 节） |

---

## 2. quality_score.schema.json 核心字段说明

### 必填字段（16 个）

| 字段 | 类型 | 说明 |
|------|------|------|
| `quality_summary` | string | 整体评估说明 |
| `scores` | object | 六大维度评分（0-10），子字段：fact_safety, doc_type_fit, mango_style_fit, logic_completeness, language_quality, risk_control |
| `threshold` | number | 达标阈值（默认 8） |
| `overall_score` | number | 综合分（六维度平均，0-10） |
| `failed_dimensions` | array | 低于 threshold 的维度名列表 |
| `overall_pass` | boolean | 所有维度 >= threshold 时 true |
| `rewrite_required` | boolean | 任一维度 < threshold 时 true |
| `quality_rewrite_instructions` | array | 给 rewrite 的可执行返修指令（每条含 dimension, target, suggested_action, reason, basis） |
| `human_review_required` | boolean | fact_safety 或 risk_control < 8 时必须 true |
| `risk_notes` | array | 风险说明列表 |
| `scoring_basis` | object | 逐维度评分依据说明 |
| `no_new_facts_check` | object | 疑似新增事实检查（含 status, suspected_new_facts, detail） |
| `doc_type_check` | object | 文种匹配检查（含 status, detail） |
| `style_check` | object | 风格检查（含 status, detail） |
| `final_output_policy` | object | 输出策略建议（recommendation: pass/rewrite/warn_and_output） |
| `quality_gate_policy` | object | 策略声明，6 个 const=true 字段 |

### quality_gate_policy 硬约束

| 字段 | const | 含义 |
|------|-------|------|
| no_body_generation | true | 不生成正文 |
| no_body_modification | true | 不修改正文 |
| no_new_facts | true | 不补充外部事实 |
| no_rag_call | true | 不调用 RAG |
| no_doc_type_change | true | 不改变文种判断 |
| evaluate_only | true | 只评估，不执行修改 |

### final_output_policy.recommendation 枚举

| 值 | 含义 |
|----|------|
| `pass` | 所有维度达标，直接输出 |
| `rewrite` | 存在不达标维度且未达最大返修次数，触发返修 |
| `warn_and_output` | 达到最大返修次数仍不达标，标记风险后输出 |

**注意**：不存在 `fail`。最差情况是 `warn_and_output`。

---

## 3. prompts/07-quality-score.md 评分逻辑摘要

### 六大维度评分范围

所有维度均为 **0-10 分**，threshold = 8。

| 维度 | 核心评估内容 | 特殊约束 |
|------|-------------|----------|
| fact_safety | final_markdown 事实是否全部来自 extract_result | 发现疑似新增事实只能指出风险，不能自行补事实 |
| doc_type_fit | 标题/结构/行文方向/格式/语气是否符合文种 | 不改变 classify_result.doc_type |
| mango_style_fit | 是否符合芒果系表达气质 | 不得以"缺少具体人物/数据"为由扣分（那是 fact_safety 的事），不得引入 RAG 旧稿事实 |
| logic_completeness | 结构完整/段落推进顺畅/信息交代清楚 | — |
| language_quality | 用词准确/凝练/正式，可交付质感 | — |
| risk_control | 称谓/机构/数据/日期/职务/敏感表达稳妥 | — |

### 评分 → 门禁逻辑

```
overall_score = 六维度平均分（保留一位小数）
overall_pass  = 所有维度 >= threshold
rewrite_required = 任一维度 < threshold
human_review_required = (fact_safety < 8) OR (risk_control < 8) OR (达到最大返修轮次)

final_output_policy:
  overall_pass=true                    → pass
  overall_pass=false AND round < max   → rewrite
  overall_pass=false AND round >= max  → warn_and_output
```

### 关键约束

- quality gate **不调用 RAG**
- quality gate **不补充外部事实**
- quality gate **不改变文种判断**
- quality gate **只评估 final_markdown**
- 低分 ≠ 硬失败，最差是 warn_and_output

---

## 4. prompts/06-rewrite.md 增强点说明

### 修改 1：新增输入变量

在现有 8 个输入变量后新增：

```
质量门禁返修意见（仅返修轮次 > 0 时存在）：
{{quality_rewrite_instructions}}
```

首次 rewrite（review → rewrite）时该变量为空，不影响现有行为。

### 修改 2：新增"质量门禁返修模式"章节

在"rewrite 核心规则"部分新增第 0 节，说明：

1. **仅在 quality_rewrite_instructions 非空时适用**
2. **优先级**：质量门禁返修指令 > review_result.rewrite_instructions
3. **硬约束完全不变**：
   - no_new_facts: true
   - no_rag_call: true
   - use_only_extract_facts: true
   - follow_review_instructions: true
   - follow_doc_type_rules: true
   - follow_org_title_dictionary: true
4. **revision_report 使用 "Q" 前缀**（Q001, Q002...）区分质量门禁修订和 review 阶段修订

### 未修改内容

- 原有 12 条核心规则全部保留
- 原有 7 种问题类型的修订策略全部保留
- 原有 4 个示例全部保留
- rewrite_policy 七项硬约束全部保留

---

## 5. 是否修改 rewrite.schema.json

### 结论：不需要修改

**理由**：

1. **revision_report 已有足够灵活性**——issue_id 是 string 类型，可使用 "Q001" 前缀标记质量门禁修订，无需新增字段
2. **resolved_issues / unresolved_issues 不需要区分来源**——质量门禁修订也是 issue，只是来源不同（Q 前缀 vs R 前缀），语义自明
3. **rewrite_policy 已包含所有硬约束**——新增的"质量门禁返修模式"的六项约束就是 rewrite_policy 的现有字段
4. **PipelineReport 可在阶段 2 新增字段**记录 quality_rewrite_round，不需要在 rewrite schema 中体现

如果后续发现需要记录质量返修轮次，建议在 `pipeline_types.py` 的 PipelineReport 中新增字段，而非修改 rewrite.schema.json。

---

## 6. JSON Schema 合法性检查

### 检查方法

使用 `jsonschema.Draft7Validator` 对 `quality_score.schema.json` 进行验证：

- ✅ JSON 语法合法
- ✅ 16 个 required 字段全部定义
- ✅ 六大维度评分范围 0-10 正确
- ✅ quality_gate_policy 六个 const=true 字段正确
- ✅ final_output_policy.recommendation 枚举包含 pass/rewrite/warn_and_output
- ✅ quality_rewrite_instructions 结构完整（含 dimension/target/suggested_action/reason/basis）
- ✅ no_new_facts_check 结构完整（含 status/suspected_new_facts/detail）

### 测试场景验证

| 测试 | 场景 | 验证结果 |
|------|------|----------|
| Test 1 | 全部通过（所有维度 10 分） | ✅ 0 errors |
| Test 2 | 低分返修（language_quality=4, mango_style_fit=5） | ✅ 0 errors |
| Test 3 | 事实风险（fact_safety=4, suspected_new_facts 存在） | ✅ 0 errors |
| Test 4 | warn_and_output（达到最大返修轮次） | ✅ 0 errors |

### 注意

`schema_loader.py` 的 SCHEMA_MAP 当前不包含 `quality_score`，因此 `load_schema('quality_score')` 会抛异常。这是预期的——SCHEMA_MAP 的扩展将在阶段 2（接入 Pipeline 执行逻辑）时进行。

---

## 7. review.score 与 quality_score 命名冲突风险评估

### 风险分析

| 风险点 | 说明 | 缓解措施 |
|--------|------|----------|
| 两个分数混淆 | review.score 是初稿合规分，quality_score 是成稿质量分 | 在 quality_summary 中明确说明"本评估对象是 rewrite 后的 final_markdown" |
| 字段名冲突 | review schema 有 `score`，quality schema 有 `overall_score` | ✅ **已规避**：quality 使用 `overall_score` 而非 `score`，避免同名字段 |
| 评分维度重叠 | review 的 fact_grounding_check 和 quality 的 fact_safety 有关联 | review 检查"draft 有没有问题"，quality 检查"final_markdown 质量够不够好"，对象不同 |
| 评分范围不同 | review.score 是 0-100，quality.scores 各维度是 0-10 | ✅ **已规避**：不同的评分范围天然区分两个分数 |

### 结论

**命名冲突风险低**。已通过以下措施规避：
1. quality 使用 `overall_score`（0-10）而非 `score`（0-100）
2. quality 使用 `scores`（对象）而非单一分值
3. quality 使用 `quality_rewrite_instructions` 而非 `rewrite_instructions`
4. quality 使用 `quality_gate_policy` 而非 `review_policy`
5. Prompt 文档中多处强调两者的定位差异

---

## 8. 当前风险点

### 高风险

1. **LLM 评分稳定性**——"成稿质量"的维度（语言质量、芒果风格）比"事实合规"更主观，LLM 可能给出不稳定分数。建议：阶段 2 端到端验证时关注评分一致性
2. **返修循环复杂度**——虽然阶段 1 只定义了契约，但后续实现"质量不达标 → rewrite → 重新评分"循环时，需要 max_rounds、成本上限、超时机制

### 中风险

3. **quality_rewrite_instructions 与 review.rewrite_instructions 优先级冲突**——两个来源的修订指令可能矛盾。Prompt 中已定义优先级（质量门禁 > review），但实际执行中需验证
4. **threshold=8 可能过高或过低**——需要真实 case 验证后调整。当前设为 8 是保守选择

### 低风险

5. **SCHEMA_MAP 未扩展**——预期在阶段 2 处理
6. **测试 case 未更新**——回归测试不需要更新（质量门禁不影响六阶段结果），但建议阶段 2 新增质量门禁的专项测试

---

## 9. 是否建议进入阶段 2

### ✅ 建议进入

**阶段 1 验收标准检查**：

| # | 验收标准 | 状态 |
|---|----------|------|
| 1 | 新增 prompts/07-quality-score.md | ✅ |
| 2 | 新增 schemas/quality_score.schema.json | ✅ |
| 3 | Schema 合法 | ✅（4 个测试场景全部通过） |
| 4 | 六大评分维度完整 | ✅ |
| 5 | 低于 8 分时 rewrite_required=true | ✅ |
| 6 | quality gate 不调用 RAG、不补事实 | ✅（quality_gate_policy 六项 const=true） |
| 7 | quality gate 是 rewrite 后置门禁，不改变六阶段主结构 | ✅（Prompt 开头明确说明） |
| 8 | rewrite prompt 能接收质量返修意见 | ✅（新增 quality_rewrite_instructions 输入变量 + 返修模式章节） |
| 9 | rewrite prompt 仍保持 no_new_facts / no_rag_call / use_only_extract_facts | ✅（返修模式六项硬约束明确列出） |
| 10 | 没有把低分写成硬失败；应是返修或 warn 输出 | ✅（final_output_policy 三个枚举值，无 fail） |

**10/10 全部通过。**

### 阶段 2 建议范围

1. 创建 `pipeline/quality_gate.py`（质量门禁核心函数）
2. 修改 `pipeline/run_pipeline.py`（插入 quality_gate 调用 + 返修循环）
3. 修改 `pipeline/pipeline_types.py`（新增 quality_score/threshold/quality_passed 等字段）
4. 修改 `pipeline/schema_loader.py`（SCHEMA_MAP 新增 quality_score）
5. 修改 `pipeline/run_pipeline.py`（新增 quality_rewrite_round 变量传递）
6. 用 1-2 个 case 端到端验证（含首次评估 + 返修 + 再次评估）
7. 输出阶段 2 验收报告

---

*报告时间：2026-05-29 07:10 UTC*
*执行者：卡乐比（OpenClaw）*
*阶段 1 结论：✅ 建议进入阶段 2（Pipeline 接入）*
