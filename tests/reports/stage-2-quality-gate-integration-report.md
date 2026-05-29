# 阶段 2 执行报告：质量门禁 Pipeline 接入

> **阶段**：2 — Pipeline 代码接入
> **版本**：mango-doc-writer v0.1.3
> **日期**：2026-05-29
> **执行者**：卡乐比（OpenClaw 助手）
> **状态**：✅ 完成

---

## 1. 修改文件清单

### 修改（4 文件）

| 文件 | 行数 | 改动内容 |
|------|------|---------|
| `pipeline/pipeline_types.py` | 127 | SCHEMA_MAP 加 `quality_score` 条目；PipelineReport 新增 11 个质量门禁字段 |
| `pipeline/run_pipeline.py` | 875 | STAGE_PROMPTS 加 `quality_score`；`_build_stage_prompt` 加质量门禁模板变量；rewrite 后插入质量门禁循环；`save_results` 加质量门禁字段序列化 |
| `pipeline/output_formatter.py` | 255 | `format_output` 加 `quality_gate` 输出块；`format_user_text` 加质量门禁人类可读文本 |
| `pipeline/schema_prompt.py` | 164 | SCHEMA_FILES 加 `quality_score` 条目 |

### 新增（阶段 1 产出，本阶段沿用）

| 文件 | 行数 | 说明 |
|------|------|------|
| `prompts/07-quality-score.md` | 631 | 六维度评分 Prompt（阶段 1 新增） |
| `schemas/quality_score.schema.json` | 378 | 16 个必填字段的评分结果 Schema（阶段 1 新增） |

### 未修改

| 文件 | 行数 | 说明 |
|------|------|------|
| `schemas/rewrite.schema.json` | 456 | 经验证完全兼容 Q 前缀 revision_report，无需改动 |
| `prompts/06-rewrite.md` | — | 阶段 1 已增强，本阶段无新改动 |
| `pipeline/model_client.py` | — | 不涉及 |
| `pipeline/rag_client.py` | — | 不涉及 |

---

## 2. 新 Pipeline 执行流程

### 核心定位

**quality gate 是 rewrite 后置门禁函数，不是第七阶段。**

对外仍保持"六阶段 Pipeline"表述不变：

```
classify → extract → plan → draft → review → rewrite
                                              ↓
                                         quality gate（后置评估函数）
                                              ↓
                                     final_markdown 输出
```

### 完整流程

```
用户初稿 + 文种需求
    ↓
01-classify → 02-extract → 03-plan → 04-draft → 05-review → 06-rewrite
                                                                      ↓
                                                          ┌─ QUALITY_GATE_ENABLED? ─┐
                                                          │                           │
                                                         NO                         YES
                                                          │                           │
                                              跳过，直接输出               调用 quality_score
                                              （v0.1.2 行为）                     ↓
                                                                     overall_pass?
                                                                      ↓         ↓
                                                                    YES        NO
                                                                     ↓          ↓
                                                              输出 + pass    rewrite_required?
                                                                     ↓          ↓     ↓
                                                                          有指令   无指令
                                                                             ↓       ↓
                                                                          回 rewrite  warn
                                                                             ↓
                                                                      下一轮评分
                                                                      （最多 N 轮）
                                                                          ↓
                                                              达到 max_rounds → warn
```

### 关键约束

1. **STAGES 列表不变**：`["classify", "extract", "plan", "draft", "review", "rewrite"]`（6 个）
2. **quality gate 不改变 classify/extract/plan/draft/review 的职责**
3. **质量返修只能回到 rewrite，不能回到 draft**
4. **quality gate 不调用 RAG、不补充事实、不改变文种判断、不生成/修改正文**

---

## 3. 质量门禁循环逻辑

### 循环结构（run_pipeline.py 第 610-770 行）

```python
if QUALITY_GATE_ENABLED:
    qg_round = 0
    while True:
        qg_round += 1
        
        # 1. 构造 payload → 调用 quality_score（复用 _run_single_stage）
        qg_result = _run_single_stage("quality_score", qg_payload)
        
        # 2. 校验失败 → 保留 final_markdown + warn_and_output + human_review
        #    （不硬失败，不丢失稿件）
        
        # 3. overall_pass=True → 输出 + 标记 pass
        
        # 4. overall_pass=False + qg_round >= max_rounds → warn_and_output
        
        # 5. overall_pass=False + 有 rewrite_instructions → 回 rewrite
        #    → 保留上一版 final_markdown（安全网）
        #    → rewrite 失败则回退上一版
```

### 三种退出路径

| 路径 | 条件 | quality_gate_pass | final_output_policy | human_review_required |
|------|------|-------------------|---------------------|----------------------|
| 通过 | `overall_pass=True` | `True` | `pass` | 按 quality_score 结果 |
| 超限 | `rounds >= max_rounds` | `False` | `warn_and_output` | `True` |
| 异常 | `_run_single_stage` 失败 | `None` | `warn_and_output` | `True` |

### 安全保障

- **final_markdown 不因 quality gate 失败而丢失**：每轮 rewrite 前保留上一版，rewrite 失败时回退
- **Schema 校验失败不静默吞掉**：异常路径写入 `quality_gate_error` 字段
- **循环上限硬约束**：`QUALITY_GATE_MAX_ROUNDS` 防止无限循环

### 返修 rewrite 调用

质量返修 rewrite 与正常 rewrite 使用**相同的 schema（rewrite.schema.json）**和**相同的 _run_single_stage 机制**，但 payload 中额外注入：

- `quality_rewrite_instructions`：质量门禁生成的返修指令（JSON 字符串）
- rewrite prompt 的 Section 0（质量门禁返修模式）被激活，六项硬约束全部 `true`

**Q 前缀约定**：质量返修的 `revision_report` 中，`issue_id` 和 `revision_id` 使用 `Q` 前缀（如 `Q001`、`Q-001`），与 review 阶段的 `R` 前缀区分来源。

---

## 4. 新增环境变量

| 变量 | 默认值 | 类型 | 说明 |
|------|--------|------|------|
| `QUALITY_GATE_ENABLED` | `true` | bool | 质量门禁总开关。`false` 时完全回退 v0.1.2 旧流程 |
| `QUALITY_GATE_THRESHOLD` | `8` | float | 六维度评分阈值（0-10）。低于此值时 `overall_pass=False` |
| `QUALITY_GATE_MAX_ROUNDS` | `2` | int | 最大返修轮次。达到后输出 `warn_and_output`，不硬失败 |

### 使用方式

```bash
# 正常启用（默认）
python pipeline/run_pipeline.py

# 禁用质量门禁（回退 v0.1.2）
QUALITY_GATE_ENABLED=false python pipeline/run_pipeline.py

# 调低阈值（更严格）
QUALITY_GATE_THRESHOLD=9 python pipeline/run_pipeline.py

# 允许更多返修轮次
QUALITY_GATE_MAX_ROUNDS=3 python pipeline/run_pipeline.py
```

---

## 5. pipeline_report 新增字段

PipelineReport dataclass 新增 11 个字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `quality_gate_enabled` | `bool` | `True` | 质量门禁是否启用 |
| `quality_gate_pass` | `Optional[bool]` | `None` | 最终是否通过（`True`/`False`/`None`=异常） |
| `quality_gate_threshold` | `float` | `8.0` | 本次使用的阈值 |
| `quality_gate_rounds_used` | `int` | `0` | 实际使用的评分轮次 |
| `quality_gate_max_rounds` | `int` | `2` | 配置的最大返修轮次 |
| `final_quality_scores` | `Optional[Dict]` | `None` | 最终一轮的六维度评分 |
| `failed_dimensions` | `List[str]` | `[]` | 低于阈值的维度名列表 |
| `quality_score_history` | `List[Dict]` | `[]` | 每轮评分的完整记录 |
| `final_output_policy` | `Optional[str]` | `None` | 最终输出策略：`pass`/`warn_and_output` |
| `human_review_required` | `bool` | `False` | 是否需要人工复核 |
| `quality_gate_error` | `Optional[str]` | `None` | 质量门禁异常信息（成功时为 `None`） |
| `quality_rewrite_applied` | `bool` | `False` | 是否执行过质量返修 |

**PipelineReport 总字段数**：40 个（阶段 1 新增前为 29 个）。

### quality_score_history 每轮记录结构

```json
{
  "round": 1,
  "overall_score": 7.2,
  "scores": {"fact_safety": 9, "doc_type_fit": 8, ...},
  "failed_dimensions": ["mango_style_fit", "language_quality"],
  "overall_pass": false,
  "rewrite_required": true,
  "human_review_required": false,
  "final_output_policy": "rewrite"
}
```

---

## 6. output_formatter 展示内容

### format_output 新增 quality_gate 块

**通过时：**
```json
{
  "quality_gate": {
    "enabled": true,
    "pass": true,
    "scores": {"fact_safety": 9, "doc_type_fit": 8, ...},
    "failed_dimensions": [],
    "rounds_used": 1,
    "max_rounds": 2,
    "rewrite_applied": false,
    "output_policy": "pass",
    "human_review_required": false,
    "score_history": [...]
  }
}
```

**异常时：**
```json
{
  "quality_gate": {
    "enabled": true,
    "pass": null,
    "error": "质量门禁调用失败 (round 1): ...",
    "output_policy": "warn_and_output",
    "human_review_required": true
  }
}
```

**禁用时：**
```json
{
  "quality_gate": {"enabled": false}
}
```

### format_user_text 新增人类可读文本

**通过：**
```
---
✅ 质量门禁通过 (fac=9 | doc=8 | man=8 | log=9 | lan=10 | ris=10)
```

**未通过（经过返修）：**
```
---
⚠️ 质量门禁未通过 (fac=9 | doc=8 | man=5 | log=8 | lan=4 | ris=9)
   低分维度: mango_style_fit, language_quality
   已完成 2/2 轮返修
   当前稿件已输出，建议人工复核低分维度
   🔴 需要人工复核
```

**异常：**
```
---
⚠️ 质量门禁异常: 质量门禁调用失败 (round 1): ...
   当前稿件已输出，建议人工复核
```

**禁用：**
```
ℹ️ 质量门禁未启用
```

---

## 7. rewrite.schema.json 兼容性验证

### 测试方法

构造包含 Q 前缀 `issue_id` / `revision_id` 的 rewrite 结果，通过 `schema_loader.validate_result("rewrite", data)` 校验。

### 测试数据要点

- `revision_report` 包含两条记录：`issue_id="Q001"`（质量返修来源）和 `issue_id="R001"`（review 修订来源）
- `revision_id` 使用 `"Q-001"` 和 `"R-001"` 前缀区分
- `resolved_issues` 同时包含 Q 和 R 前缀

### 验证结果

```
✅ rewrite.schema.json 完全兼容 Q 前缀 issue_id + revision_id
```

**结论**：rewrite.schema.json 的 `issue_id` 和 `revision_id` 字段均为 `type: string`，无正则约束或枚举限制，Q 前缀天然兼容。**无需修改 Schema。**

---

## 8. QUALITY_GATE_ENABLED=false 回退验证

### 代码路径

```python
# run_pipeline.py 第 614 行
qg_enabled = _os.getenv("QUALITY_GATE_ENABLED", "true").lower() == "true"

# 第 770-773 行
else:
    # QUALITY_GATE_ENABLED=false，完全回到 v0.1.2 旧流程
    print("\n  ℹ️ 质量门禁已禁用 (QUALITY_GATE_ENABLED=false)")
    report.quality_gate_enabled = False
    report.quality_gate_pass = None
```

### 验证要点

| 验证项 | 结果 |
|--------|------|
| 不调用 `_run_single_stage("quality_score", ...)` | ✅ 整个 `if qg_enabled:` 块被跳过 |
| 不进入 while 循环 | ✅ 不执行任何评分/返修逻辑 |
| `report.quality_gate_enabled = False` | ✅ 明确标记门禁未启用 |
| `report.quality_gate_pass = None` | ✅ 与"通过"和"未通过"区分 |
| STAGES 遍历不受影响 | ✅ STAGES 仍为 6 阶段 |
| save_results 正常序列化 | ✅ quality_gate 字段有默认值，不会序列化出错 |
| format_output 展示 `{"enabled": false}` | ✅ 代码路径正确 |

### 回退时的完整执行路径

```
QUALITY_GATE_ENABLED=false
  → 跳过质量门禁 if 块
  → 进入 else 块
  → report.quality_gate_enabled = False
  → report.quality_gate_pass = None
  → 直接进入 save_results → format_output
  → 输出与 v0.1.2 完全一致（额外字段均为默认值）
```

---

## 9. Schema 校验结果

### 校验工具

`pipeline/schema_loader.py` → `jsonschema.validate()`

### 校验项目

| 项目 | Schema | 结果 |
|------|--------|------|
| rewrite + Q 前缀 revision_report | `rewrite.schema.json` | ✅ 通过 |
| quality_score schema 加载 | `quality_score.schema.json` | ✅ 通过 |
| quality_score + 全部通过 | `quality_score.schema.json` | ✅ 通过 |
| quality_score + 低分返修 | `quality_score.schema.json` | ✅ 通过 |
| quality_score + 事实风险 | `quality_score.schema.json` | ✅ 通过 |
| quality_score + warn_and_output | `quality_score.schema.json` | ✅ 通过 |

**总结**：6 项 Schema 校验全部通过。

---

## 10. 语法 / Import / Mock 验证结果

### 语法检查（AST 解析）

| 文件 | 结果 |
|------|------|
| `run_pipeline.py` | ✅ syntax OK |
| `pipeline_types.py` | ✅ syntax OK |
| `output_formatter.py` | ✅ syntax OK |
| `schema_loader.py` | ✅ syntax OK |
| `schema_prompt.py` | ✅ syntax OK |

### 模块导入验证

```
✅ pipeline_types import OK
✅ schema_loader import OK
✅ schema_prompt import OK
✅ output_formatter import OK
✅ run_pipeline import OK
```

### 注册表一致性验证

```
STAGES: ['classify', 'extract', 'plan', 'draft', 'review', 'rewrite']
SCHEMA_MAP keys: ['classify', 'extract', 'plan', 'draft', 'review', 'rewrite', 'quality_score']
SCHEMA_FILES keys: ['classify', 'extract', 'plan', 'draft', 'review', 'rewrite', 'quality_score']
```

**结论**：
- STAGES 保持 6 个阶段不变 ✅
- SCHEMA_MAP 和 SCHEMA_FILES 均包含 `quality_score`（作为辅助 schema，非阶段）✅
- 三者保持一致 ✅

---

## 11. 当前风险点

### 高风险

| # | 风险 | 影响 | 缓解措施 |
|---|------|------|---------|
| 1 | **未经真实 LLM 调用验证** | quality gate 的 prompt + schema 在实际 DeepSeek 调用中可能产生不符合预期的输出，导致 jsonschema 校验失败走 warn_and_output 路径 | 异常路径已有兜底（保留 final_markdown + warn），不会丢稿件；阶段 3 建议端到端集成测试 |
| 2 | **quality_score prompt 模板变量未实测** | `{{quality_rewrite_round}}` 和 `{{max_quality_rewrite_rounds}}` 的模板渲染路径未经过真实调用验证 | 代码中 `_build_stage_prompt` 已添加分支处理，但需阶段 3 端到端验证 |

### 中风险

| # | 风险 | 影响 | 缓解措施 |
|---|------|------|---------|
| 3 | **质量返修 rewrite 可能与 review rewrite 行为不一致** | rewrite prompt 的 Section 0（质量门禁返修模式）在真实调用中可能被模型忽略 | Section 0 已设置六项硬约束全部 `true`，且 prompt 中明确指令"必须优先执行 Q 前缀指令" |
| 4 | **多轮返修的 token 消耗** | 每轮返修 = 1 次 quality_score 调用 + 1 次 rewrite 调用，2 轮最大 = 额外 4 次 LLM 调用 | `QUALITY_GATE_MAX_ROUNDS` 可配置，默认 2 轮有限；且 threshold=8 大部分稿件应在首轮通过 |
| 5 | **PipelineReport 字段膨胀** | 从 29 个字段增至 40 个，pipeline_report.json 体积增大 | 不影响功能，可接受 |

### 低风险

| # | 风险 | 影响 | 缓解措施 |
|---|------|------|---------|
| 6 | **environment variable 解析** | `QUALITY_GATE_THRESHOLD` 用 `float()` 转换，非法值会抛异常 | 阶段 3 可增加 try/except + 默认值回退 |
| 7 | **output_formatter 中 quality_gate 展示格式** | 人类可读文本的格式细节（维度缩写、换行等）可能需调整 | 纯展示层，不影响核心功能 |

---

## 12. 是否建议进入阶段 3

**建议：✅ 进入阶段 3 — 端到端集成测试**

### 理由

1. **阶段 2 代码接入已完成**：5 个模块语法正确、import 成功、Schema 校验通过、逻辑路径完整
2. **核心风险在于真实 LLM 调用**：质量门禁的所有异常路径已有兜底，但需要端到端验证 prompt → LLM → jsonschema → 循环逻辑的完整链路
3. **低分处理策略已就位**：warn_and_output 不硬失败的设计已编码验证

### 阶段 3 建议目标

1. 使用真实素材（或最小测试素材）跑完整 Pipeline
2. 验证 quality_score 的 LLM 输出是否符合 Schema
3. 验证质量返修 → rewrite 回路的实际效果
4. 验证 `QUALITY_GATE_ENABLED=false` 回退路径的端到端行为
5. 验证 output_formatter 的格式化输出

### 阶段 3 前置条件

- [x] 阶段 1 合约定义完成（prompt + schema）
- [x] 阶段 2 Pipeline 接入完成
- [ ] DeepSeek API 可用（需确认 key 有效）
- [ ] 准备最小测试素材（一段简短新闻稿素材 + 明确文种）

---

## 附录：代码修改统计

| 指标 | 阶段 1 | 阶段 2 | 累计 |
|------|--------|--------|------|
| 新增文件 | 2 | 0 | 2 |
| 修改文件 | 1 | 4 | 4（阶段 1 修改 prompts/06-rewrite.md） |
| 新增代码行 | ~1000 | ~200 | ~1200 |
| PipelineReport 字段 | 29 | 40 | +11 |
| STAGES 数量 | 6 | 6 | 不变 |
| SCHEMA_MAP 条目 | 6 | 7 | +1 |

---

*报告结束。mango-doc-writer v0.1.3 质量门禁代码接入完成，建议进入阶段 3 端到端集成测试。*
