# Stage 22 — Quality Gate 功能报告

**日期**: 2026-05-29
**版本**: v0.1.3
**状态**: 完成

---

## 1. 本阶段目标

在不改变六阶段 Pipeline 主结构的前提下，为 mango-doc-writer 增加 rewrite 后置质量门禁能力，实现"AI 成稿质量评分 + 自动返修闭环"。

## 2. 新增功能概述

### 2.1 后置质量门禁

rewrite 完成后，系统可选执行 quality gate，对 final_markdown 进行六维度评分。

**定位**：quality gate 是 rewrite 后的后置评估函数，**不是第七阶段**。六阶段 STAGES 不变：classify → extract → plan → draft → review → rewrite。

### 2.2 六大评分维度

| 维度 | 评估内容 | 评分标准 |
|------|----------|----------|
| fact_safety | 事实安全 | 是否新增了用户未提供的事实 |
| doc_type_fit | 文种匹配 | 标题、结构、格式是否符合文种规范 |
| mango_style_fit | 芒果风格 | 表达是否符合芒果系气质 |
| logic_completeness | 逻辑完整 | 结构是否完整、信息是否交代清楚 |
| language_quality | 语言质量 | 用词是否准确、凝练、正式 |
| risk_control | 风险控制 | 称谓、机构、数据、敏感表达是否稳妥 |

每个维度 0-10 分，阈值默认 8。

### 2.3 自动返修闭环

- 所有维度 ≥ 阈值 → 通过，直接输出
- 任一维度 < 阈值 → 生成 quality_rewrite_instructions，交给 rewrite 执行定点改进
- rewrite 修订后再次评分，循环直到通过或达到最大返修轮次

### 2.4 warn_and_output 机制

达到最大返修轮次仍不通过时：
- 保留稿件
- 标记风险
- human_review_required = true
- 提示人工复核

**注意**：不存在"硬失败"，最差情况是 warn_and_output。

## 3. 最终流程

```
rewrite 输出 final_markdown
    ↓
quality_score 评分（六维度）
    ↓
  ┌─ 所有维度 ≥ 阈值 → pass，输出 final_markdown
  │
  └─ 任一维度 < 阈值 → rewrite_required = true
       ↓
     quality_rewrite_instructions 交给 rewrite
       ↓
     rewrite 执行定点修订，输出新 final_markdown
       ↓
     quality_score 再次评分
       ↓
       ┌─ 通过 → pass
       └─ 仍不通过 → 继续循环，直到达到最大轮次
                          ↓
                     warn_and_output：保留稿件，标记风险，提示人工复核
```

## 4. 六大评分维度（详细）

### fact_safety（事实安全）

检查 final_markdown 中的事实是否全部来自用户输入、extract_result 和 pipeline 已确认事实，无新增事实。

- 10 分：全部事实可追溯，无任何疑似新增
- 8-9 分：极少量模糊表述，不构成事实性新增
- 6-7 分：存在 1-2 处疑似新增事实
- 4-5 分：多处置疑新增事实
- 0-3 分：大量新增事实或严重编造

### doc_type_fit（文种匹配）

检查标题、结构、行文方向、格式、语气是否符合 classify_result 和 doc-type-rules。

### mango_style_fit（芒果风格）

检查是否符合湖南广电/芒果体系的表达气质。**硬约束**：风格评估不得引入 RAG 旧稿中的具体人物、数据、活动。

### logic_completeness（逻辑完整）

检查结构是否完整、段落推进是否顺畅、信息是否交代清楚。

### language_quality（语言质量）

检查用词是否准确、凝练、正式，是否具备可交付成稿质感。

### risk_control（风险控制）

检查称谓、机构、数据、日期、职务、敏感表达是否稳妥。

## 5. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| QUALITY_GATE_ENABLED | true | 质量门禁开关，false 时回退 v0.1.2 旧流程 |
| QUALITY_GATE_THRESHOLD | 8 | 达标阈值（0-10），维度分低于此值视为不达标 |
| QUALITY_GATE_MAX_ROUNDS | 2 | 最大返修轮次，达到后仍不通过则 warn_and_output |

## 6. 修改文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| prompts/07-quality-score.md | 新增 | 质量门禁评分 Prompt |
| schemas/quality_score.schema.json | 新增 | 质量门禁输出 Schema |
| pipeline/run_pipeline.py | 修改 | 接入 quality gate 循环逻辑 |
| pipeline/pipeline_types.py | 修改 | PipelineReport 新增 quality_gate_* 字段 |
| tests/regression/test_quality_gate.py | 新增 | 22 项质量门禁测试 |
| tests/fixtures/quality_score_pass.json | 新增 | 测试 fixture：全部通过 |
| tests/fixtures/quality_score_warn.json | 新增 | 测试 fixture：warn_and_output |
| tests/fixtures/quality_score_rewrite.json | 新增 | 测试 fixture：返修场景 |
| tests/fixtures/quality_score_fact_risk.json | 新增 | 测试 fixture：事实风险 |
| deploy/env.example | 修改 | 新增 QUALITY_GATE_* 环境变量 |
| docs/mango-doc-writer-architecture.md | 修改 | 新增 Quality Gate 架构说明 |
| docs/mango-doc-writer-developer-guide.md | 修改 | 新增质量门禁维护指南 |
| docs/mango-doc-writer-release-notes.md | 修改 | 新增 v0.1.3 release notes |
| docs/mango-doc-writer-user-guide.md | 修改 | 新增质量检查说明 |
| docs/stage-22-quality-gate-report.md | 新增 | 本报告 |

## 7. 测试验证摘要

| 测试 | 结果 |
|------|------|
| 质量门禁测试套件（22 项） | 22/22 通过 |
| Fixtures Schema 校验（4 个） | 4/4 通过 |
| Prompt JSON 示例校验（6 个） | 6/6 通过 |
| 枚举一致性检查（Prompt vs Schema） | 全部一致 |
| Pipeline 代码改动 | 无破坏性变更 |
| v0.1.2 兼容性 | QUALITY_GATE_ENABLED=false 可回退 |

### 测试场景覆盖

| 场景 | 测试项 |
|------|--------|
| A. 质量通过 | test_A_quality_pass |
| B. 风格低分→返修→通过 | test_B_style_rewrite_then_pass |
| C. 持续低分→warn_and_output | test_C_max_rounds_warn_and_output |
| D. fact_safety<8→human_review | test_D_fact_safety_human_review |
| E. 门禁关闭→回退旧流程 | test_E_disabled_fallback |
| F. max_rounds=0/1 | test_F_max_rounds_zero/one |
| G. 门禁调用异常 | test_G_quality_gate_exception |
| H. rewrite 失败→保留上一版 | test_H_rewrite_failure_preserves_markdown |
| I. 无返修指令→warn_and_output | test_I_no_instructions_warn |
| Schema 校验 | 5 项 |
| PipelineReport 序列化 | 3 项 |
| 六阶段不变验证 | 4 项 |

## 8. 风险与限制

### 8.1 风险

1. **Prompt 依赖**：评分质量取决于模型对 Prompt 的理解和遵循程度
2. **阈值固定**：默认阈值 8 分可能不适合所有场景
3. **返修不保证收敛**：某些问题可能在多次返修后仍无法解决
4. **Token 消耗**：每轮 quality gate 会额外消耗一次 LLM 调用

### 8.2 限制

1. **质量分不等于事实真伪保证**：quality gate 无法验证事实的真伪
2. **不覆盖排版质量**：只评估文本内容，不评估排版输出
3. **不调用 RAG**：评估时不检索风格案例或历史文稿
4. **不补充外部事实**：只基于六阶段已有结果评估

### 8.3 人工复核边界

以下情况必须人工复核：
- fact_safety < 8：存在疑似新增事实
- risk_control < 8：存在风险控制隐患
- 达到最大返修轮次后仍存在低于阈值的维度

**重要**：
- 系统不能无人值守正式发稿
- 涉及领导职务、机构名称、日期、金额、数据、政策表述等仍需人工核对

## 9. 是否建议发布 v0.1.3

**✅ 建议发布 v0.1.3。**

理由：
1. 全部测试通过（22/22）
2. Schema 校验通过（4/4 fixtures + 6/6 Prompt 示例）
3. 枚举一致性已验证
4. 文档已完整更新
5. v0.1.2 兼容性已保证
6. 人工复核边界已明确
