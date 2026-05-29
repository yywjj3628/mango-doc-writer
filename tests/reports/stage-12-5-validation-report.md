# 阶段 12.5 验证报告

**执行时间**: 2026-05-28 13:00 UTC (北京时间 21:00)
**执行状态**: 部分通过

---

## 1. 是否成功接入 OpenClaw 模型调用器

✅ **是。** 通过 `openclaw agent --session-id {id} --message {prompt} --json --timeout {s}` CLI 命令成功接入。

## 2. call_stage() 实现方式

- **文件**: `pipeline/model_runner.py`
- **调用方式**: subprocess 调用 `openclaw agent` CLI
- **Prompt 构造**: 加载 `prompts/{stage}.md` + 注入模板变量 + reference 文件
- **JSON 提取**: 多层策略（直接解析 → 代码块提取 → 大括号匹配 → 修复未转义引号）
- **RAG 调用**: 仅 draft 阶段通过 `localhost:8000/search` 调用 style_rag

## 3. 每个阶段是否真实调用模型

| 阶段 | 是否调用 | 响应时间 | 状态 |
|------|---------|---------|------|
| classify | ✅ | 19-24s | ✅ JSON 解析成功 + Schema 校验通过 |
| extract | ✅ | 20-24s | ✅ JSON 解析成功 + Schema 校验通过 |
| plan | ✅ | 31s | ❌ Schema 校验失败 (additionalProperties) |
| draft | ❌ | - | 未执行 (plan 失败后停止) |
| review | ❌ | - | 未执行 |
| rewrite | ❌ | - | 未执行 |

## 4. 每个阶段是否通过 schema 校验

| 阶段 | 校验结果 | 说明 |
|------|---------|------|
| classify | ✅ 通过 | `doc_type=请示`, `conflict_detected=true` |
| extract | ✅ 通过 | 7 个顶层键全部符合 schema |
| plan | ❌ 失败 | `manual_confirmation_fields` 的 item 包含额外字段 `impact` |

## 5. 002 case 执行结果

### classify 阶段
- **doc_type**: 请示 ✅ （正确识别为请示，非报告）
- **conflict_detected**: true ✅
- **risk_level**: critical ✅
- **style_level**: 1 ✅
- **direction**: 上行文 ✅
- **Schema 校验**: ✅ 通过

### extract 阶段
- **Schema 校验**: ✅ 通过
- 抽取了请求预算支持的事实

### plan 阶段
- **Schema 校验**: ❌ 失败
- **错误**: `manual_confirmation_fields` 的 item 包含 `impact` 字段，但 `plan.schema.json` 定义 `additionalProperties: false`，只允许 `field`、`reason`、`suggestion`
- **根本原因**: 模型在 manual_confirmation_fields 的 item 中输出了额外的 `impact` 字段，schema 定义过于严格
- **备注**: 这是 schema 定义和模型输出之间的兼容性问题，不是 prompt 问题

### draft/review/rewrite
- 未执行（plan 失败后停止）

## 6. 009 case 执行结果

❌ 未执行（002 case plan 阶段失败后，优先修复问题再执行 009）

## 7. 是否出现 invalid_json

❌ 未出现。classify 首次出现中文引号问题，已修复 `_extract_json` 增加 `_fix_unescaped_quotes`。

## 8. 是否出现 schema_validation_error

✅ **是。** plan 阶段出现 `additionalProperties` 违规。

**具体错误**:
```
Additional properties are not allowed ('impact' was unexpected)
Instance: manual_confirmation_fields[5] = {
  "field": "预算金额",
  "impact": "high",  // ← 不在 schema 中
  "reason": "请示事项涉及预算但无金额",
  "suggestion": "确认预算金额或明确概括性表述"
}
```

## 9. 是否出现事实新增

未到 draft 阶段，无法确认。

## 10. 是否出现 RAG 污染

未到 draft 阶段，无法确认。

## 11. final_markdown 是否生成

❌ 未生成（pipeline 在 plan 阶段失败）。

## 12. review 是否发现问题

❌ 未执行。

## 13. rewrite 是否修复问题

❌ 未执行。

## 14. 当前遗留问题

### P0: plan.schema.json 中 manual_confirmation_fields 定义过于严格

`plan.schema.json` 中 `manual_confirmation_fields` 的 item 定义为:
```json
{
  "additionalProperties": false,
  "properties": {
    "field": {"type": "string"},
    "reason": {"type": "string"},
    "suggestion": {"type": "string"}
  },
  "required": ["field", "reason"]
}
```

模型在 item 中输出了额外的 `impact` 字段（表示该确认事项的影响程度），但 schema 不允许。

**可能的解决方案**:
1. 放宽 schema：将 `additionalProperties` 改为 `true`
2. 在 `_extract_json` 中过滤额外字段（不修改 schema）
3. 在 prompt 中明确要求 manual_confirmation_fields 的 item 只包含 field/reason/suggestion

**注意**: 按照阶段 12.5 规则，不得修改 prompts/schemas/references。此问题需要用户决策。

### P1: openclaw agent 注入大量系统上下文

`openclaw agent` 会注入 AGENTS.md、SOUL.md、TOOLS.md 等 ~50KB 的系统上下文，可能导致模型注意力分散。已通过 force_prefix/force_suffix 缓解。

### P2: 模型输出中未转义的 ASCII 双引号

GLM-5-Turbo 在 JSON 字符串值内使用未转义的 ASCII 双引号（如 `"请求"`），破坏 JSON 结构。已实现 `_fix_unescaped_quotes` 修复。

## 15. 是否建议进入全量 10 case 测试

❌ **不建议**。需先解决 plan 阶段 schema 兼容性问题。

## 16. 是否建议进入 typeset-engine

❌ **不建议**。核心 pipeline 尚未跑通，先修复 schema 问题。

---

## 技术细节

### 新增文件
- `pipeline/model_runner.py` — 模型调用适配器（12.6KB）

### 修改文件
- `pipeline/run_pipeline.py` — 导入改为从 model_runner 获取 call_stage
- `pipeline/pipeline_types.py` — PipelineReport.status 默认值修复

### MODEL_RUNNER_CONNECTED
- **值**: True
- **位置**: `pipeline/model_runner.py`

### 调用链路
```
run_pipeline()
  → _build_stage_payload(stage, input_data, completed)
  → _run_single_stage(stage, payload)
    → call_stage(stage, payload)  # model_runner.py
      → _build_stage_prompt(stage, payload)  # 加载 prompt + 渲染模板
      → _call_openclaw_agent(prompt, session_id, timeout)  # subprocess
      → _extract_json(raw_text)  # 多策略 JSON 提取
    → validate_result(stage, result)  # jsonschema.validate
```
