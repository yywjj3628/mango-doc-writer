# 阶段 0 执行报告：AI 成稿质量评分门禁 — 审计

> **执行时间**：2026-05-29 06:03 UTC
> **执行内容**：只读审计，不修改任何文件
> **目标**：评估"AI 成稿质量评分门禁"的可行插入位置与影响范围

---

## 1. 确认的当前 Pipeline 流程

```
用户输入 (requirement + draft)
    │
    ▼
input_parser  →  PipelineInput
    │
    ▼
┌──────────────────────────────────────────────────┐
│              六阶段串联 Pipeline                    │
│                                                    │
│  01 classify  →  classify_result.json              │
│       │                                            │
│  02 extract   →  extract_result.json                │
│       │                                            │
│  03 plan      →  plan_result.json                  │
│       │                                            │
│  04 draft     →  draft_result.json                  │
│       │  (唯一调用 style_rag 的阶段)                  │
│  05 review    →  review_result.json                │
│       │  (不生成正文，不调用 RAG)                      │
│  06 rewrite   →  rewrite_result.json               │
│       │  (不调用 RAG，输出 final_markdown)             │
└──────────────────────────────────────────────────┘
    │
    ▼
output_formatter  →  pipeline_report.json + final_markdown.md
    │
    ▼ (可选)
render_pipeline  →  typeset-engine  →  DOCX / PDF
```

**关键确认**：
- Pipeline 是严格串行的，`for stage in STAGES` 顺序执行
- 每阶段输出经 `jsonschema.validate` 校验
- 任一阶段失败即停止（`return PipelineResult(status="failed")`）
- **不存在循环/重试机制**——rewrite 之后没有"回到 review"或"回到 draft"的逻辑
- `run_pipeline.py` 中无 `while` 循环、无 `max_retries`（模型调用重试在 model_client 层）

---

## 2. 确认的关键文件路径

### Pipeline 核心

| 文件 | 职责 |
|------|------|
| `pipeline/run_pipeline.py` | 六阶段串联主入口（~450 行） |
| `pipeline/pipeline_types.py` | 类型定义（STAGES, PipelineInput, StageResult, PipelineReport, PipelineResult） |
| `pipeline/model_client.py` | DeepSeek API 调用 |
| `pipeline/model_runner.py` | 模型调用器接口层 |
| `pipeline/rag_client.py` | 多 Collection RAG 检索 |
| `pipeline/schema_loader.py` | JSON Schema 加载 |
| `pipeline/schema_prompt.py` | Schema Guard 注入 |
| `pipeline/input_parser.py` | 输入解析 |
| `pipeline/output_formatter.py` | 输出格式化 |

### 六阶段 Prompt

| 文件 | 阶段 |
|------|------|
| `prompts/01-classify.md` | 文种识别 |
| `prompts/02-extract.md` | 事实抽取 |
| `prompts/03-plan.md` | 结构规划 |
| `prompts/04-draft.md` | 初稿生成 |
| `prompts/05-review.md` | 质检审查 |
| `prompts/06-rewrite.md` | 二次修订 |

### 六阶段 Schema

| 文件 | 阶段 |
|------|------|
| `schemas/classify.schema.json` | classify |
| `schemas/extract.schema.json` | extract |
| `schemas/plan.schema.json` | plan |
| `schemas/draft.schema.json` | draft |
| `schemas/review.schema.json` | review |
| `schemas/rewrite.schema.json` | rewrite |

### 知识库

| 文件 | 职责 |
|------|------|
| `references/doc-type-rules.md` | 10+ 文种规则 |
| `references/org-title-dictionary.yaml` | 机构称谓/领导职务/禁用称谓 |
| `references/style-rag-policy.md` | RAG 使用边界 |
| `references/mango-style-guide.md` | 芒果风格指南 |
| `references/output-templates.md` | 输出模板 |
| `references/forbidden-expressions.md` | 禁用表达 |

### 测试与报告

| 目录/文件 | 职责 |
|-----------|------|
| `tests/cases/` | 10 个标准测试 case |
| `tests/regression/` | 回归测试工具 |
| `tests/reports/` | 阶段报告 |

---

## 3. "AI 成稿质量评分门禁"建议插入位置

### 方案对比

| 位置 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **A. rewrite 之后，output_formatter 之前** | 不改变六阶段结构，只做后置门禁；可访问全部六阶段结果 | 无法触发自动修复，只能 warn/block | ⭐⭐⭐⭐ |
| **B. review 之后，rewrite 之前** | 可根据评分决定是否需要 rewrite | review 已有 score/pass/rewrite_required，职责重叠 | ⭐⭐ |
| **C. review 内部** | 不新增阶段 | review 已有评分职责，模糊边界 | ⭐ |
| **D. 新增第七阶段 quality_gate** | 结构清晰，独立职责 | 违背"不建议大规模重构 pipeline"原则 | ⭐⭐ |

### 推荐方案：A — rewrite 之后，output_formatter 之前

**理由**：

1. **不改变现有六阶段结构**——符合"不建议大规模重构 Pipeline"原则
2. **review 和 quality_score 职责清晰分离**：
   - review：做"逐项事实/文种/称谓/RAG 检查"，输出 issues + rewrite_instructions
   - quality_score：做"成稿整体质量评估"，给出综合分数和是否达标的门禁判断
3. **可访问 final_markdown 全文**——基于成稿而非初稿评分
4. **不影响 rewrite 行为**——rewrite 仍然只根据 review_result 执行定点修订
5. **可循环扩展**——后续如需"quality_score 不达标 → 重新 draft → review → rewrite"闭环，可增量实现

**实现方式**（非阶段，而是后置函数）：

```
review → rewrite → [quality_gate(final_markdown, classify, extract, plan, draft, review, rewrite)] → output_formatter
```

在 `run_pipeline.py` 的 `run_pipeline()` 函数中，在 `final_markdown` 提取后、`return PipelineResult` 前插入：

```python
# ─── 质量门禁（非阶段，后置评估） ───────────────────────────
quality_result = run_quality_gate(
    final_markdown=final_markdown,
    classify_result=classify_result,
    extract_result=extract_result,
    plan_result=plan_result,
    draft_result=draft_result,
    review_result=review_result,
    rewrite_result=rewrite_result,
)
report.quality_score = quality_result["score"]
report.quality_passed = quality_result["passed"]
report.quality_issues = quality_result["issues"]
```

---

## 4. 需要新增/修改的文件清单

### 新增文件

| 文件 | 职责 |
|------|------|
| `pipeline/quality_gate.py` | 质量门禁核心逻辑（评分 + 门禁判断） |
| `prompts/07-quality-gate.md` | 质量评分 Prompt（如用 LLM 评分） |
| `schemas/quality_gate.schema.json` | 质量评分输出 Schema |

### 需修改文件

| 文件 | 修改内容 | 影响范围 |
|------|----------|----------|
| `pipeline/run_pipeline.py` | 在 rewrite 后插入 `quality_gate` 调用 | 仅新增 ~15 行 |
| `pipeline/pipeline_types.py` | PipelineReport 新增 `quality_score`, `quality_passed`, `quality_issues` 字段 | 仅新增 3 个字段 |
| `tests/regression/run_regression.py` | 报告中展示 quality_gate 结果 | 仅展示层 |
| `docs/mango-doc-writer-architecture.md` | 数据流简图新增 quality_gate | 仅文档 |

### 不需要修改的文件

- `prompts/01~06-*.md` — 六阶段 Prompt 不动
- `schemas/classify~rewrite.schema.json` — 六阶段 Schema 不动
- `references/*` — 知识库不动
- `pipeline/rag_client.py` — RAG 客户端不动
- `render/*` — 排版层不动

---

## 5. 当前代码中是否已有类似实现

### 逐项检查

| 检查项 | 结论 | 依据 |
|--------|------|------|
| **review.score** | ✅ 已有 | review.schema.json 定义 `score: integer, 0-100`；05-review.md 有扣分规则 |
| **review.pass** | ✅ 已有 | review.schema.json 定义 `pass: boolean`；有明确的 pass 判断规则 |
| **review.rewrite_required** | ✅ 已有 | review.schema.json 定义 `rewrite_required: boolean`；有硬性联动规则 |
| **quality_score（独立阶段）** | ❌ 不存在 | 无第七阶段，无 quality_gate 文件 |
| **循环 rewrite** | ❌ 不存在 | run_pipeline.py 是单次 `for` 循环，rewrite 后没有回到 review/draft 的逻辑 |
| **门禁判断（score 阈值阻断）** | ❌ 不存在 | review.score 不达标时 rewrite_required=true，但不会阻断输出，pipeline 仍然输出 final_markdown |
| **PipelineReport.quality_score** | ❌ 不存在 | PipelineReport 无此字段 |

### 关键发现

1. **review.score 是"初稿质检分"**，评估的是 draft_result 的合规性（事实溯源/文种/称谓/RAG），不是 final_markdown 的成稿质量
2. **review.score 不阻断输出**——即使 score < 85 且 pass=false，rewrite 仍然执行并输出 final_markdown
3. **无循环修复机制**——rewrite 只执行一次，不根据 rewrite 结果再次 review
4. **无独立的成稿质量评分**——final_markdown 生成后没有二次质量评估

---

## 6. review.score 与拟新增 quality_score 的职责差异

| 维度 | review.score | quality_score（拟新增） |
|------|-------------|----------------------|
| **评估对象** | draft_result.markdown_draft（初稿） | rewrite_result.final_markdown（成稿） |
| **评估时机** | review 阶段（rewrite 之前） | rewrite 之后，output 之前 |
| **评估维度** | 事实溯源、文种合规、称谓准确、RAG 污染、结构合规 | 成稿完整性、逻辑连贯、表达质量、文种一致性、整体可读性 |
| **核心问题** | "draft 有没有问题？" | "final_markdown 质量够不够好？" |
| **输出目的** | 给 rewrite 提供修订指令 | 给用户/下游提供质量评估和门禁判断 |
| **是否阻断** | 不阻断，只影响 rewrite_required | 可配置门禁阈值阻断（quality_passed=false 时 warn 或 block） |
| **是否调用 RAG** | ❌ 禁止 | ❌ 禁止（同理，RAG 仍不能用于补事实） |
| **是否生成正文** | ❌ 禁止 | ❌ 禁止 |
| **评分依据** | issues 类型+数量+级别 | 可综合 six-stage 全量信息 + 成稿全文 |

### 职责边界总结

> **review 负责"找问题"**——逐项检查 draft 是否违反规则，输出 issues 和 rewrite_instructions。
>
> **quality_score 负责"评质量"**——评估 rewrite 后的 final_markdown 整体质量，给出门禁判断。
>
> 两者不重叠：review 评估初稿、输出修订指令；quality_score 评估成稿、输出质量结论。

---

## 7. RAG 约束确认

**quality_score 阶段仍然不能使用 RAG 补充事实。**

理由：

1. RAG 的定位在 `style-rag-policy.md` 中明确为 **style_rag（风格案例检索层）**，禁止补充事实
2. RAG 只允许在 **draft 阶段** 调用一次——这是硬约束，写入 draft_policy
3. review、rewrite 均不调用 RAG（review_policy.no_rag_call=true, rewrite_policy.no_rag_call=true）
4. quality_score 作为后置评估，评估依据必须是：
   - final_markdown 全文
   - classify_result（文种/风险）
   - extract_result（事实来源）
   - review_result（issues/rewrite_instructions）
   - rewrite_result（revision_report/resolved_issues）
   - doc-type-rules.md（文种规则）
   - org-title-dictionary.yaml（称谓口径）
5. **RAG 仍不能用于**：补领导职务、补机构名称、补数据、补事实、评价质量

---

## 8. 风险点

### 高风险

1. **quality_score 与 review.score 混淆**——两个分数可能导致用户困惑。建议明确区分：review_score = 初稿合规分，quality_score = 成稿质量分
2. **门禁阻断影响工作流**——如果 quality_passed=false 时阻断输出，可能影响用户紧急使用。建议默认 warn + score，可选 block

### 中风险

3. **评分主观性**——"成稿质量"的评估维度（表达质量、逻辑连贯、可读性）比"事实合规"更主观，LLM 评分可能不稳定
4. **新增 LLM 调用成本**——如用 LLM 评分，每次 pipeline 多一次 API 调用（可用 flash 模型控制成本）
5. **循环 rewrite 的复杂度**——如果后续扩展为"quality_score 不达标 → 循环 draft→review→rewrite"，复杂度显著上升，需要设置最大循环次数、成本上限、超时机制

### 低风险

6. **PipelineReport 字段新增**——向后兼容，新增字段不影响已有输出
7. **回归测试**——10 个 case 不需要重新跑（quality_gate 是新增后置步骤，不影响六阶段结果）

---

## 9. 是否建议进入阶段 1

### ✅ 建议，有条件进入

**条件**：

1. **保持"后置门禁"设计**——不新增第七阶段，不改变六阶段结构
2. **quality_score 不调用 RAG**——严格遵守 style-rag-policy.md
3. **quality_score 不生成正文、不重写正文**——纯评估，无副作用
4. **默认 warn 模式**——quality_passed=false 时输出警告而非阻断，用户可配置 block
5. **循环 rewrite 不在阶段 1 范围**——先做单次评分+门禁，循环机制列为后续可选

### 不建议立即做的

- ❌ 新增第七阶段（打破六阶段稳定结构）
- ❌ 循环 draft→review→rewrite（复杂度太高，需要 max_rounds + 成本控制）
- ❌ 用 RAG 评估质量（RAG 不能用于事实补充，也不能用于质量评估中的事实验证）
- ❌ 修改六阶段 Prompt 或 Schema（先验证后置门禁方案）

### 阶段 1 建议范围

1. 创建 `pipeline/quality_gate.py`
2. 创建 `prompts/07-quality-gate.md`
3. 创建 `schemas/quality_gate.schema.json`
4. 修改 `pipeline/run_pipeline.py`（插入调用）
5. 修改 `pipeline/pipeline_types.py`（新增字段）
6. 用 1-2 个 case 端到端验证
7. 输出阶段 1 验收报告

---

## 10. 验收标准检查

| # | 验收标准 | 状态 |
|---|----------|------|
| 1 | 不修改任何代码 | ✅ |
| 2 | 能准确说明 review 与 quality_score 的职责差异 | ✅（见第 6 节） |
| 3 | 能准确说明 RAG 仍然不能用于补事实 | ✅（见第 7 节） |
| 4 | 确认当前无类似评分/门禁/循环 rewrite 实现 | ✅（见第 5 节） |
| 5 | 确认关键文件路径 | ✅（见第 2 节） |
| 6 | 确认当前 Pipeline 流程 | ✅（见第 1 节） |
| 7 | 给出建议插入位置 | ✅（见第 3 节） |
| 8 | 给出需要新增/修改的文件清单 | ✅（见第 4 节） |
| 9 | 列出风险点 | ✅（见第 8 节） |
| 10 | 给出是否建议进入阶段 1 的结论 | ✅（见第 9 节） |

**10/10 全部通过。**

---

*报告时间：2026-05-29 06:10 UTC*
*执行者：卡乐比（OpenClaw）*
*阶段 0 结论：✅ 建议进入阶段 1（有条件）*
