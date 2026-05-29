# 阶段 2 执行报告：质量门禁 Pipeline 接入

> **执行时间**：2026-05-29 07:30 UTC
> **执行内容**：将 quality gate 接入 Pipeline 执行逻辑（rewrite 之后、output_formatter 之前）
> **不涉及**：classify / extract / plan / draft / review 职责变更、RAG 路由修改、DeepSeek API 客户端修改

---

## 1. 修改文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **修改** | `pipeline/pipeline_types.py` | SCHEMA_MAP 新增 `quality_score`；PipelineReport 新增 13 个质量门禁字段 |
| **修改** | `pipeline/run_pipeline.py` | STAGE_PROMPTS 新增 `quality_score`；`_build_stage_prompt` 支持 quality_score 变量；主流程新增质量门禁循环；`save_results` 序列化质量门禁字段 |
| **修改** | `pipeline/output_formatter.py` | `format_output` 新增 `quality_gate` 输出段；`format_user_text` 新增质量门禁展示（4 种状态） |
| **修改** | `pipeline/schema_prompt.py` | SCHEMA_FILES 新增 `quality_score` |
| 未修改 | `pipeline/schema_loader.py` | 无需修改（已通过 SCHEMA_MAP 自动支持） |
| 未修改 | `schemas/rewrite.schema.json` | 经验证，Q 前缀 issue_id 兼容（无 pattern/enum 约束） |
| 未修改 | `pipeline/model_client.py` | 复用现有 call_llm_json 机制 |

---

## 2. 新 Pipeline 执行流程

```
用户初稿
    ↓
classify → extract → plan → draft → review → rewrite
    ↓
┌─────────────────────────────────────────┐
│     质量门禁循环（后置函数，非第七阶段）    │
│                                         │
│  quality_score(prompt + schema validation)│
│       ↓                                 │
│  overall_pass=true? ──→ pass → output  │
│       ↓ No                              │
│  round >= max_rounds? ──→ warn → output │
│       ↓ No                              │
│  有返修指令? ──→ rewrite(带Q指令) → 回到  │
│  quality_score                         │
│       ↓ No                              │
│  warn_and_output → output              │
└─────────────────────────────────────────┘
    ↓
output_formatter → 用户输出
```

**对外表述**：仍为"六阶段 Pipeline"。Quality gate 是后置门禁函数。

---

## 3. 质量门禁循环逻辑

### 流程伪代码

```
qg_round = 0
quality_history = []
quality_rewrite_applied = False

while True:
    qg_round += 1
    
    # 1. 构造 quality_score payload
    qg_payload = {所有已完成阶段结果} + {quality_rewrite_round, max_rounds}
    
    # 2. 调用 quality_score（复用 _run_single_stage）
    try:
        qg_result = _run_single_stage("quality_score", qg_payload)
    except:
        # 调用失败 → 保留 final_markdown，标记 error
        report.quality_gate_error = "..."
        report.final_output_policy = "warn_and_output"
        break
    
    if qg_result.status == "failed":
        # 校验失败 → 保留 final_markdown，标记 error
        report.quality_gate_error = "..."
        report.final_output_policy = "warn_and_output"
        break
    
    # 3. 记录本轮评分到 quality_score_history
    
    # 4. 判断结果
    if overall_pass:
        → pass，记录 scores，退出循环
    elif qg_round >= max_rounds:
        → warn_and_output，标记 human_review_required，退出循环
    elif 无返修指令:
        → warn_and_output，退出循环
    else:
        → 返修：
           - 保留 prev_final_markdown（安全网）
           - rewrite(payload含 quality_rewrite_instructions)
           - 如果 rewrite 失败 → 保留 prev_final_markdown，warn，退出
           - 如果 rewrite 成功 → 更新 completed["rewrite"], 继续
```

### 关键约束

- **只能回到 rewrite**，不能回到 draft
- **最多 QUALITY_GATE_MAX_ROUNDS 轮**（默认 2）
- **不硬失败**：最差情况是 warn_and_output
- **final_markdown 不会丢失**：调用失败或返修失败均保留上一版

---

## 4. 新增环境变量

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `QUALITY_GATE_ENABLED` | `true` | 设为 `false` 完全回到 v0.1.2 旧流程 |
| `QUALITY_GATE_THRESHOLD` | `8` | 质量达标阈值（0-10），低于此值触发返修 |
| `QUALITY_GATE_MAX_ROUNDS` | `2` | 质量返修最大轮次，防止无限循环 |

### 解析逻辑

```python
qg_enabled = os.getenv("QUALITY_GATE_ENABLED", "true").lower() == "true"
qg_threshold = float(os.getenv("QUALITY_GATE_THRESHOLD", "8"))
qg_max_rounds = int(os.getenv("QUALITY_GATE_MAX_ROUNDS", "2"))
```

大小写不敏感（`True`/`true`/`TRUE` 均识别为启用）。

---

## 5. pipeline_report 新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `quality_gate_enabled` | bool | True | 是否启用质量门禁 |
| `quality_gate_pass` | Optional[bool] | None | 最终是否通过（None=未评估/异常） |
| `quality_gate_threshold` | float | 8.0 | 使用的阈值 |
| `quality_gate_rounds_used` | int | 0 | 实际使用的评分轮次 |
| `quality_gate_max_rounds` | int | 2 | 配置的最大轮次 |
| `final_quality_scores` | Optional[Dict] | None | 最终六维度评分 |
| `failed_dimensions` | List[str] | [] | 最终低分维度列表 |
| `quality_score_history` | List[Dict] | [] | 每轮评分历史（含 round, scores, pass, policy） |
| `final_output_policy` | Optional[str] | None | pass / rewrite / warn_and_output |
| `human_review_required` | bool | False | 是否需要人工复核 |
| `quality_gate_error` | Optional[str] | None | 异常原因（如有） |
| `quality_rewrite_applied` | bool | False | 是否发生了质量返修 |

所有字段均通过 `save_results` 序列化到 `pipeline_report.json`。

---

## 6. output_formatter 展示内容

### format_output 新增输出段

```json
"quality_gate": {
  "enabled": true,
  "pass": true,
  "scores": {"fact_safety": 9, "doc_type_fit": 9, ...},
  "failed_dimensions": [],
  "rounds_used": 1,
  "max_rounds": 2,
  "rewrite_applied": false,
  "output_policy": "pass",
  "human_review_required": false,
  "score_history": [...]
}
```

### format_user_text 新增展示（4 种状态）

**状态 1：通过**
```
✅ 质量门禁通过 (fac=9 | doc=9 | man=8 | log=9 | lan=9 | ris=10)
   经过 2 轮质量返修
```

**状态 2：未通过**
```
⚠️ 质量门禁未通过 (fac=8 | doc=8 | man=5 | log=7 | lan=6 | ris=9)
   低分维度: mango_style_fit, language_quality
   已完成 2/2 轮返修
   当前稿件已输出，建议人工复核低分维度
   🔴 需要人工复核
```

**状态 3：异常**
```
⚠️ 质量门禁异常: API timeout
   当前稿件已输出，建议人工复核
   🔴 需要人工复核
```

**状态 4：未启用**
```
ℹ️ 质量门禁未启用
```

### 不夸大表述

- 通过时不说"自动保证可发稿"
- 未通过时明确说"当前稿件已输出，**建议**人工复核"
- 异常时明确说"建议人工复核"

---

## 7. rewrite.schema.json 兼容性验证

### 验证方式

```python
jsonschema.validate(instance={
    "revision_report": [
        {"issue_id": "Q001", "status": "resolved", ...},
        {"issue_id": "R001", "status": "resolved", ...}
    ]
}, schema=rewrite_schema)
```

### 验证结果

| 检查项 | 结果 | 说明 |
|--------|------|------|
| issue_id 类型 | ✅ | `type: string`，无 pattern/enum 约束，Q001 合法 |
| quality_rewrite_used 字段 | ✅ | **不在 rewrite.schema.json 中**（additionalProperties=false），模型不会输出此字段。质量返修信息通过 Pipeline 执行层传递，不写入 rewrite result |
| revision_report Q 前缀 | ✅ | issue_id 是自由 string，R 前缀（review）和 Q 前缀（quality）均可 |

### 结论

**不需要修改 rewrite.schema.json**。阶段 1 的设计决策正确：
- 返修指令通过 payload 传入 rewrite prompt，不在 rewrite schema 中体现
- 返修轮次通过 PipelineReport 记录，不在 rewrite schema 中体现

---

## 8. QUALITY_GATE_ENABLED=false 验证

### 验证方式

```python
os.environ["QUALITY_GATE_ENABLED"] = "false"
enabled = os.getenv("QUALITY_GATE_ENABLED", "true").lower() == "true"
# → enabled = False
```

### 验证结果

| 检查项 | 结果 |
|--------|------|
| 环境变量解析 | ✅ `false` → `enabled=False` |
| 大小写不敏感 | ✅ `True`/`true`/`TRUE` 均为启用 |
| Pipeline 代码路径 | ✅ `if qg_enabled:` 块跳过，直接到 `else:` 分支 |
| else 分支行为 | ✅ `report.quality_gate_enabled = False; quality_gate_pass = None`，完全回到 v0.1.2 旧流程 |

### 旧流程保证

当 `QUALITY_GATE_ENABLED=false` 时：
1. rewrite 之后直接提取 final_markdown
2. 不调用 quality_score
3. 不进入返修循环
4. pipeline_report 中 quality_gate 相关字段为默认值（enabled=False, pass=None）
5. output_formatter 显示"质量门禁未启用"

---

## 9. Schema 校验

### 运行验证

- ✅ `quality_score.schema.json` 通过 jsonschema 校验（16 required fields 全部定义）
- ✅ `quality_score.schema.json` 通过 `load_schema('quality_score')` 加载
- ✅ `build_schema_guard('quality_score')` 生成 1870 字符约束文本
- ✅ rewrite.schema.json Q 前缀兼容（issue_id type=string 无约束）
- ✅ Pipeline 代码中 `_run_single_stage("quality_score", payload)` 会自动走 sanitizer + schema validation

### quality_score Schema Guard 自动生成

自动提取的约束包括：
- additionalProperties: false
- 3 个 enum 约束（final_output_policy.recommendation, no_new_facts_check.status, doc_type_check.status, style_check.status）
- 16 个 required 字段
- string 字段不得为 null

---

## 10. 最小流程测试

### 测试 1：Python 模块导入验证

```
✅ SCHEMA_MAP 包含 quality_score
✅ quality_score schema 加载成功（16 required fields）
✅ quality_score schema guard 生成成功（1870 chars）
✅ PipelineReport 包含全部 13 个质量门禁字段
✅ PipelineReport 质量门禁默认值正确
✅ output_formatter 导入成功
✅ STAGE_PROMPTS 包含 quality_score
```

### 测试 2：环境变量解析

```
✅ QUALITY_GATE_ENABLED=false → enabled=False
✅ QUALITY_GATE_ENABLED=true → enabled=True
✅ QUALITY_GATE_ENABLED=True → enabled=True（大小写不敏感）
✅ threshold=8.0, max_rounds=2（默认值正确）
```

### 测试 3：output_formatter 4 种状态展示

```
✅ 质量门禁通过：显示六维度评分 + 返修轮次
✅ 质量门禁未通过：显示低分维度 + "建议人工复核低分维度" + 🔴
✅ 质量门禁异常：显示错误 + "建议人工复核" + 🔴
✅ 质量门禁未启用：显示"质量门禁未启用"
```

### 测试 4：语法检查

```
✅ run_pipeline.py 语法正确
✅ pipeline_types.py 语法正确
✅ output_formatter.py 语法正确
✅ schema_loader.py 语法正确
✅ schema_prompt.py 语法正确
```

### 未运行

- **端到端真实 LLM 调用**：需要 DEEPSEEK_API_KEY，留待阶段 3 端到端验证
- **回归测试**：质量门禁不影响六阶段结果，但需确认现有测试不受影响

---

## 11. 当前风险点

### 高风险

1. **LLM 评分稳定性**：quality_score 的语言质量、芒果风格维度较主观，LLM 可能给出不稳定分数。需要真实 case 验证后调整 threshold。
2. **返修循环成本**：每轮返修 = 1 次 quality_score + 1 次 rewrite，最多 2 轮 = 额外 4 次 API 调用。需监控 token 消耗。

### 中风险

3. **quality_rewrite_instructions 优先级**：Prompt 中定义"质量门禁 > review"，但实际执行中两者可能给出矛盾指令。
4. **threshold=8 可能过高/过低**：需真实 case 调优。
5. **output_formatter 中的质量门禁异常路径**：如果 quality_score 调用成功但结果格式异常，sanitizer 可能修复不当。

### 低风险

6. **save_results 序列化**：新增字段均为简单类型，无序列化风险。
7. **环境变量类型转换**：`float()` / `int()` 可能抛 ValueError，但部署环境可控。

---

## 12. 是否建议进入阶段 3

### ✅ 建议进入

**阶段 2 验收标准检查**：

| # | 验收标准 | 状态 |
|---|----------|------|
| 1 | quality gate 插在 rewrite 后、output_formatter 前 | ✅ 代码位于 rewrite 提取 final_markdown 之后、return PipelineResult 之前 |
| 2 | 对外仍保持六阶段 Pipeline，不称第七阶段 | ✅ 注释中明确"后置函数，非第七阶段" |
| 3 | QUALITY_GATE_ENABLED=false 可回到旧流程 | ✅ 验证通过，else 分支完全跳过质量门禁 |
| 4 | 低分只回 rewrite，不回 draft | ✅ 代码中只有 rewrite 返修路径，无 draft 返修 |
| 5 | 最多返修 2 轮，不能无限循环 | ✅ while 循环受 qg_max_rounds 控制 |
| 6 | 达到最大轮次仍不通过时 warn_and_output，不硬失败 | ✅ max_rounds 分支输出 final_output_policy="warn_and_output" |
| 7 | pipeline_report 能记录每轮质量评分 | ✅ quality_score_history 记录每轮 round/scores/pass/policy |
| 8 | quality_score 经过 schema validation | ✅ 复用 _run_single_stage，自动 sanitizer + validate_result |
| 9 | quality gate 不调用 RAG、不补事实 | ✅ quality_score prompt 中无 RAG 注入；_build_stage_prompt 中 quality_score 不注入 rag_info |
| 10 | final_markdown 不会因 quality gate 失败而丢失 | ✅ 所有失败路径保留 prev_final_markdown 或跳过质量门禁 |

**10/10 全部通过。**

### 阶段 3 建议范围

1. 端到端真实 case 验证（至少 2 个 case：一个通过、一个触发返修）
2. 评分稳定性测试（同一 case 多次运行，观察 score 波动）
3. threshold 调优建议
4. 确认 v0.1.2 现有功能不受回归影响
5. 输出阶段 3 验收报告
6. **考虑是否正式发布 v0.1.3**

---

*报告时间：2026-05-29 07:30 UTC*
*执行者：卡乐比（OpenClaw）*
*阶段 2 结论：✅ 10/10 验收标准全部通过，建议进入阶段 3（端到端验证）*
