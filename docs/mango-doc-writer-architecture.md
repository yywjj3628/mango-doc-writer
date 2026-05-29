# mango-doc-writer 架构说明

## 总体架构

```
用户初稿 + 文种需求
    ↓
┌─────────────────────────────────────────────────────────┐
│                    六阶段管线（主结构不变）                 │
│  classify → extract → plan → draft → review → rewrite   │
└─────────────────────────────────────────────────────────┘
    ↓
final_markdown.md
    ↓
┌─────────────────────────────────────────────────────────┐
│         quality gate（后置质量门禁，v0.1.3 新增）          │
│  六维度评分 → 通过/返修/warn_and_output                    │
│  ⚠️ 不是第七阶段，不改变六阶段主结构                       │
│  ⚠️ 不调用 RAG，不补充外部事实                             │
└─────────────────────────────────────────────────────────┘
    ↓
final_markdown.md（主输出）
    ↓
┌─────────────────────────────────────────────────────────┐
│                    render 模块                            │
│  final_markdown → typeset-engine → DOCX/PDF（可选）       │
└─────────────────────────────────────────────────────────┘
```

## 三层知识分工

### rules_db（规则层）

文件：`references/doc-type-rules.md`

职责：定义每种文种的写作规范、结构要求、禁忌事项。

- 公文类必须有主送单位、落款、日期
- 报告不得夹带请示事项
- 请示必须一文一事
- 通知不得写成新闻稿

### facts_db（事实层）

文件：`references/org-title-dictionary.yaml`

职责：定义机构称谓口径、领导职务规范。

- 正式机构全称
- 领导姓名 + 职务对照
- 禁用称谓列表
- 称谓不确定时标记待确认

### style_rag（风格层）

文件：由 RAG 系统提供（style-rag-policy.md 定义使用边界）

职责：提供芒果系写作风格参考。

- 只提供表达风格，不提供事实
- 不补充领导职务
- 不补充机构名称
- 不补充活动数据

## 六阶段链路

```
classify  → 文种识别、冲突检测、风险评估
    ↓
extract   → 事实抽取、缺失标记、风险标记
    ↓
plan      → 结构规划、事实绑定、禁止项标记
    ↓
draft     → 正文生成、RAG 风格引用
    ↓
review    → 事实溯源、文种检查、称谓检查、RAG 检查
    ↓
rewrite   → 定向修订、最终输出 final_markdown
    ↓
[quality gate] → 后置质量门禁（可选）
```

## pipeline 职责

文件：`pipeline/run_pipeline.py`

- 串联六阶段
- 管理阶段间数据传递
- 生成 pipeline_report.json
- 错误处理和回退
- 质量门禁循环（rewrite → quality_score → rewrite → ...）

## regression 职责

目录：`tests/regression/`

- `check_report.py`：六阶段输出完整性 + schema + 策略检查
- `check_markdown_claims.py`：final_markdown 内容扫描（观察词 + per-case 规则）
- `run_regression.py`：批量运行 + 汇总输出
- `watchlist.yaml`：三类观察词表

## render 职责

目录：`render/`

- `render_pipeline.py`：Markdown → typeset-engine JSON → DOCX/PDF
- `doc_type_mapping.yaml`：文种→排版模板映射
- `render_types.py`：类型定义

## Markdown-first 输出策略

- **所有文种**：必须输出 final_markdown.md
- **公文类**（请示/报告/通知/函/通报）：默认同时生成 DOCX
- **非公文类**（新闻稿/讲话稿/总结/汇报材料/会议纪要）：默认只生成 Markdown
- **用户明确指定**：传入 --format docx 时生成 DOCX

## typeset-engine 边界

**可以：**
- 调整版式（页边距、行距、字体）
- 调整标题样式（字号、加粗）
- 调整段落样式
- 生成 DOCX / PDF

**不可以：**
- 新增事实
- 修改正文含义
- 修正文种
- 替代 review / rewrite
- 调用 RAG
- 参与六阶段流程

## 为什么 RAG 不能作为事实来源

1. RAG 检索的是历史文稿，历史文稿中的事实可能过时
2. RAG 可能返回其他活动、其他领导的信息
3. RAG 的匹配基于语义相似度，不基于事实准确性
4. RAG 旧稿中的"领导高度肯定"可能是另一个活动的

因此：RAG 只用于风格参考，事实必须来自用户初稿。

## Quality Gate 后置质量门禁（v0.1.3 新增）

### 定位

quality gate 是 rewrite 完成后的后置质量评估函数，**不是第七阶段**。六阶段 Pipeline 主结构不变。

### 输入

quality gate 接收六阶段全部结果作为输入：

| 输入 | 来源 |
|------|------|
| classify_result | classify 阶段输出 |
| extract_result | extract 阶段输出 |
| plan_result | plan 阶段输出 |
| draft_result | draft 阶段输出 |
| review_result | review 阶段输出 |
| rewrite_result | rewrite 阶段输出（含 final_markdown） |
| quality_rewrite_round | 当前返修轮次（首次为 0） |
| max_quality_rewrite_rounds | 最大返修轮次 |

### 输出

| 输出 | 说明 |
|------|------|
| scores | 六维度评分（0-10） |
| overall_score | 综合分（六维度平均） |
| failed_dimensions | 低于阈值的维度列表 |
| quality_rewrite_instructions | 给 rewrite 的定点返修指令 |
| final_output_policy | 输出策略：pass / rewrite / warn_and_output |
| human_review_required | 是否需要人工复核 |
| quality_gate_policy | 六项策略声明（全部 true） |

### 流程

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

### 约束

- **只回到 rewrite**：quality gate 只将返修指令交给 rewrite，不回到 draft 或更早阶段
- **不调用 RAG**：quality gate 评估时不检索风格案例或历史文稿
- **不补充事实**：只基于六阶段已有结果评估，不新增外部事实
- **不修改正文**：quality gate 只输出评估 JSON，实际修改由 rewrite 执行
- **不改变文种**：以 classify_result.doc_type 为准
