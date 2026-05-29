# mango-doc-writer

湖南芒果系文案生产统一入口 — OpenClaw Skill。

## 系统目标

将用户提供的素材/初稿，按照芒果系官方文风和公文规范，生成结构化成稿。

核心价值：**规则库决定"能不能这么写"，称谓库决定"应该怎么称呼"，用户素材决定"事实是什么"，RAG 决定"写得像不像芒果系"，质量门禁决定"能不能交出去"。**

## 文件结构

```
mango-doc-writer/
├── SKILL.md                          # Skill 定义（触发条件、流程、规则）
├── README.md                          # 本文件
├── references/                        # 知识库
│   ├── doc-type-rules.md              # 公文文种规则库（10+文种）
│   ├── org-title-dictionary.yaml     # 机构与领导称谓口径库
│   ├── mango-style-guide.md           # 芒果风格指南
│   ├── output-templates.md            # 输出模板
│   └── forbidden-expressions.md      # 禁用表达列表
├── prompts/                           # 流程 Prompt
│   ├── 01-classify.md                 # 文种识别
│   ├── 02-extract.md                  # 事实抽取
│   ├── 03-plan.md                     # 结构规划
│   ├── 04-draft.md                    # 初稿生成
│   ├── 05-review.md                   # 质检
│   ├── 06-rewrite.md                  # 二次修订
│   └── 07-quality-score.md            # 质量门禁（后置评估）
├── schemas/                           # JSON Schema（各流程输出格式）
│   ├── classify.schema.json
│   ├── extract.schema.json
│   ├── plan.schema.json
│   ├── draft.schema.json
│   ├── review.schema.json
│   ├── rewrite.schema.json
│   └── quality_score.schema.json      # 质量门禁输出格式
└── tests/                             # 测试用例
    ├── cases/                         # 输入用例（001-news ~ 010-terminology-risk）
    ├── fixtures/                      # 质量门禁测试 fixtures
    ├── regression/                    # 回归测试
    └── reports/                       # 测试报告
```

## 生成流程

```
用户初稿 + 文种需求 + [generation_mode]
  → classify（识别文种）
  → extract（抽取事实）
  → plan（结构规划）
  → draft（初稿生成）
  → review（质检）
  → rewrite（二次修订）
  → [quality gate（后置质量门禁）]  ← 可选，不改变六阶段主结构
  → output Markdown 成稿
```

### Generation Mode（v0.1.4 新增）

通过 `generation_mode` 参数控制扩写行为：

| 模式 | 阈值 | 扩写 | official_use_allowed | 用途 |
|------|:----:|:----:|:-------------------:|------|
| `safe_official`（默认） | 8.0 | 禁止 | true | 正式公文 |
| `assisted_expansion` | 7.0 | 允许 | requires_human_confirmation | 内部草稿 |
| `creative_mimic` | 6.0 | 允许 | false | 灵感参考 |

**fact_safety / risk_control 始终保持 8.0 最低阈值，不随模式降低。**

默认 `safe_official` 与 v0.1.3 完全兼容，无需修改任何现有输入。

### 质量门禁（v0.1.3 新增）

rewrite 完成后，系统可选执行后置质量门禁，对 final_markdown 进行六维度评分：

- **fact_safety**（事实安全）：是否新增了用户未提供的事实
- **doc_type_fit**（文种匹配）：标题、结构、格式是否符合文种规范
- **mango_style_fit**（芒果风格）：表达是否符合芒果系气质
- **logic_completeness**（逻辑完整）：结构是否完整、信息是否交代清楚
- **language_quality**（语言质量）：用词是否准确、凝练、正式
- **risk_control**（风险控制）：称谓、机构、数据、敏感表达是否稳妥

**评分逻辑：**
- 所有维度 ≥ 8 分（可配置）→ 通过，直接输出
- 任一维度 < 8 分 → 触发质量返修，quality_rewrite_instructions 交给 rewrite 执行定点改进
- 达到最大返修轮次仍不通过 → `warn_and_output`：保留稿件，标记风险，提示人工复核

**重要边界：**
- 质量门禁不是第七阶段，六阶段 Pipeline 主结构不变
- 质量门禁不调用 RAG、不补充外部事实
- 质量分不等于事实真伪保证，涉及领导职务、机构名称、日期、金额、数据、政策表述等仍需人工核对
- 可通过 `QUALITY_GATE_ENABLED=false` 关闭，回退 v0.1.2 旧流程

## 三类知识分层

| 层 | 职责 | 文件 |
|---|---|---|
| rules_db | "能不能这么写" | doc-type-rules.md |
| facts_db | "应该怎么称呼" | org-title-dictionary.yaml |
| style_rag | "写得像不像" | RAG (hunan_mango) |

## 输入输出示例

### 输入

**safe_official（默认，v0.1.3 兼容）：**

```json
{
  "requirement": "请改成向集团汇报的正式报告，芒果系正式文风。",
  "draft": "上个月我们做了很多工作，劲舞团DAU稳定在XX万..."
}
```

**assisted_expansion（增强草拟）：**

```json
{
  "requirement": "请帮我写一篇芒果系新闻稿初稿。",
  "draft": "4月15日芒果超媒办了AI大赛，12个团队参加。",
  "generation_mode": "assisted_expansion"
}
```

**creative_mimic（风格仿写）：**

```json
{
  "requirement": "请模仿芒果系领导讲话风格写一篇稿子。",
  "draft": "会上讨论了明年的工作方向。",
  "generation_mode": "creative_mimic"
}
```

### 输出

```json
{
  "classify": { "doc_type": "报告", "direction": "上行文" },
  "extract": { "facts": { "organizations": ["久之润"], "products": ["劲舞团"] } },
  "review": { "pass": true, "score": 85 },
  "final_markdown": "# 关于XX情况的报告\n\n...",
  "need_manual_confirmation": []
}
```

## 禁止事项

1. ❌ 凭空新增事实、数据、荣誉、领导评价
2. ❌ 报告中夹带请示事项
3. ❌ 请示一文多事
4. ❌ 使用禁用称谓
5. ❌ RAG 事实污染（旧稿领导职务/数据进入新稿）
6. ❌ 缺失称谓时自行补全
7. ❌ 一次性重构全部系统
8. ❌ 删除现有 mango-writer / typeset-engine

## 与现有系统的关系

- **mango-writer**：保留不动，本 Skill 在其基础上扩展文种规则和质检闭环
- **typeset-engine**：保留不动，后续可选接入渲染
- **gongwen-writing-guide**：内容整合进 doc-type-rules.md
- **RAG**：保留不动，定位明确为 style_rag

## 最小 Pipeline 调用

Pipeline 入口：`pipeline/run_pipeline.py`

单 case 运行：
```bash
cd skills/mango-doc-writer
python scripts/run_case.py tests/cases/002-fake-report-real-request.md
```

全量 case 运行：
```bash
python scripts/run_all_cases.py
```

输出报告位置：`tests/reports/`

**阶段 12.5 状态**：模型调用器已接入（`MODEL_RUNNER_CONNECTED=True`），通过 `openclaw agent` CLI 调用 GLM-5-Turbo。002 case 在 plan 阶段出现 schema `additionalProperties` 兼容性问题（详见 `tests/reports/stage-12-5-validation-report.md`）。

所有阶段结果必须通过 `jsonschema.validate` 校验（参见 [pipeline/README.md](pipeline/README.md)）。

## 测试样例

共 10 个黄金测试样例，覆盖 8 种文种 + 2 个风险场景，用于验证六阶段闭环的约束合规性。

详见 [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md)。

## 开发阶段

共 13 阶段，严格按顺序推进，每阶段独立提交。

详见 SKILL.md 底部阶段表。

## classify 文种识别示例

**说明：classify 阶段只识别文种，不生成正文。**

### 输入

```json
{
  "requirement": "请写一份报告，向集团汇报项目情况，并请求集团给予专项预算支持。",
  "draft": "目前项目已完成前期筹备，但后续推广需要专项预算支持，拟请集团给予经费保障。",
  "specified_doc_type": "报告",
  "target_unit": "集团",
  "scene": null
}
```

### classify 输出

```json
{
  "doc_type": "请示",
  "doc_type_confidence": 0.92,
  "direction": "上行文",
  "target_unit": "集团",
  "scene": "向上级请求专项预算支持",
  "style_level": 1,
  "risk_level": "critical",
  "reason": "用户虽然指定为报告，但内容包含请求预算支持，属于请示信号，推荐判断为请示。",
  "required_rules": ["请示"],
  "required_structure": ["请示缘由", "必要性与依据", "请示事项", "请求批示"],
  "forbidden_items": [
    "不得一文多事",
    "不得多头主送",
    "不得写成报告",
    "不得缺少明确请示事项",
    "不得编造预算金额和审批依据"
  ],
  "possible_confusions": [
    {
      "candidate": "报告",
      "reason": "如果删除请求预算支持内容，仅保留项目情况汇报，则可按报告处理。",
      "distinguish_rule": "是否请求上级批准、支持、拨款或批复。"
    }
  ],
  "user_specified_doc_type": "报告",
  "conflict_detected": true,
  "conflict_reason": "用户指定为报告，但内容包含请求预算支持，符合请示特征。",
  "recommended_action": "建议改为请示；如必须写成报告，应删除请求预算支持和请予保障等请示事项。",
  "need_manual_confirmation": true,
  "manual_confirmation_fields": [
    "请确认最终文种为请示还是报告",
    "请确认是否保留请求预算支持事项"
  ]
}
```

> 此示例展示了“伪报告真请示”的冲突识别能力：classify 检测到用户指定“报告”但内容信号指向“请示”，自动标记冲突并要求人工确认。

## extract 事实抽取示例

**说明：extract 阶段只抽取用户提供的事实，不生成正文，不调用 RAG，不补充外部事实。**

### 输入

```json
{
  "requirement": "请写一份报告，向集团汇报项目情况，并请求集团给予专项预算支持。",
  "draft": "目前项目已完成前期筹备，但后续推广需要专项预算支持，拟请集团给予经费保障。",
  "classify_result": {
    "doc_type": "请示",
    "direction": "上行文",
    "risk_level": "critical",
    "conflict_detected": true
  }
}
```

### extract 输出（关键片段）

```json
{
  "source_summary": "用户素材涉及项目筹备进展和向集团请求专项预算支持事项。",
  "facts": {
    "requests": ["请求集团给予专项预算支持", "拟请集团给予经费保障"],
    "achievements": ["项目已完成前期筹备"],
    "problems": ["后续推广需要专项预算支持"]
  },
  "fact_items": [
    {
      "type": "request",
      "value": "请求集团给予专项预算支持",
      "source_text": "请求集团给予专项预算支持",
      "confidence": 0.96,
      "can_use_in_draft": true,
      "needs_manual_confirmation": false,
      "note": "该事实支持 classify 阶段判断为请示。"
    }
  ],
  "missing_fields": [
    {"field": "项目正式名称", "reason": "用户仅写\"项目\"", "impact": "影响标题准确性"},
    {"field": "预算金额", "reason": "未提供具体金额", "impact": "影响请示明确性"}
  ],
  "cannot_infer": [
    {"field": "预算金额", "reason": "用户未提供，不得自动补充"}
  ],
  "risk_flags": [
    {"type": "request_without_amount", "detail": "请求预算但无金额", "level": "high"}
  ],
  "extraction_policy": {
    "only_user_provided_facts": true,
    "no_external_knowledge": true,
    "no_rag_facts": true,
    "no_invented_data": true
  }
}
```

> 此示例展示：extract 从伪报告真请示素材中准确抽取请求事项、标记缺失字段和风险，且不补充用户未提供的预算金额。

## plan 结构规划示例

**说明：plan 阶段只做结构规划，不生成正文，不调用 RAG，不补充用户未提供的事实。**

### 输入（classify + extract 结果）

```json
{
  "classify": {
    "doc_type": "请示", "conflict_detected": true, "risk_level": "critical"
  },
  "extract": {
    "requests": ["请求集团给予专项预算支持"],
    "missing_fields": [{"field": "项目正式名称"}, {"field": "预算金额"}]
  }
}
```

### plan 输出（关键片段）

```json
{
  "doc_type": "请示",
  "title_plan": {
    "recommended_title": "关于申请专项预算支持的请示",
    "title_confidence": 0.7,
    "title_risks": ["项目正式名称缺失"]
  },
  "sections": [
    {
      "section_id": "S1",
      "section_name": "请示缘由",
      "fact_bindings": [{"fact_type": "achievement", "source_from_extract": true}],
      "blocked_items": ["不得编造项目正式名称"]
    },
    {
      "section_id": "S3",
      "section_name": "请示事项",
      "blocked_items": ["不得编造预算金额"]
    }
  ],
  "manual_confirmation_fields": [
    {"field": "文种确认", "reason": "伪报告真请示冲突"},
    {"field": "主送单位全称"},
    {"field": "落款单位"}
  ],
  "draft_directives": {
    "must_use_facts": ["项目已完成前期筹备", "请求集团给予专项预算支持"],
    "must_avoid": ["不得写成报告", "不得编造预算金额"]
  }
}
```

> 此示例展示：plan 基于请示标准四段式规划结构，每个 section 绑定 extract 事实，标记缺失字段和人工确认项，为 draft 阶段提供清晰写作指令。

## draft 初稿生成示例

**说明：draft 阶段生成 Markdown 正文初稿，是整个流程中第一次允许生成正文、第一次允许使用 style_rag。但 RAG 只用于风格参考，不作为事实来源。draft 不是最终稿，后续还要 review 和 rewrite。**

### 输入（classify + extract + plan 结果）

```json
{
  "classify": {"doc_type": "请示", "conflict_detected": true, "risk_level": "critical"},
  "extract": {"requests": ["请求集团给予专项预算支持"], "missing_fields": [{"field": "预算金额"}]},
  "plan": {"sections": [{"section_name": "请示缘由"}, {"section_name": "请示事项"}], "draft_directives": {"must_avoid": ["不得编造预算金额"]}}
}
```

### style_references

本次未获得 RAG 风格参考。

### draft 输出（关键片段）

```json
{
  "markdown_draft": "# 关于申请给予项目专项预算支持的请示\n\n【主送单位待确认】：\n\n一、请示缘由\n\n目前相关前期筹备工作已完成……\n\n三、请示事项\n\n拟请集团给予该项目专项预算支持。\n\n妥否，请批示。",
  "fact_usage_report": [{"draft_text": "前期筹备工作已完成", "source": "extract_result.fact_items"}],
  "rag_usage_report": [],
  "terminology_usage_report": [{"raw_value": "集团", "needs_manual_confirmation": true}],
  "blocked_items_check": [{"item": "预算金额", "status": "not_used"}],
  "warnings": [{"level": "critical", "type": "missing_field", "message": "预算金额缺失"}],
  "draft_policy": {"body_generated": true, "no_new_facts": true, "rag_used_for_style_only": true}
}
```

> 此示例展示：draft 生成 Markdown 正文初稿，每个事实可溯源到 extract_result，RAG 未使用时 warnings 提示，禁止项逐一检查，缺失字段和文种冲突完整承接。

## review 质检示例

**说明：review 阶段不生成正文，不重写正文，不调用 RAG。只对 draft 初稿进行事实溯源、文种规则、称谓口径、RAG 使用、禁止项、风险提示的全面审查，输出结构化质检报告，结果交给 rewrite 阶段使用。**

### 输入（draft_result + classify + extract + plan）

```json
{
  "classify": {"doc_type": "请示", "conflict_detected": true},
  "extract": {"achievements": ["项目已完成前期筹备"], "cannot_infer": [{"field": "项目预期成效"}]},
  "draft": {"markdown_draft": "……取得显著成效……"}
}
```

### review 输出（关键片段）

```json
{
  "pass": false,
  "score": 65,
  "rewrite_required": true,
  "checks": {
    "fact_grounding_check": {"status": "fail", "issues_count": 1},
    "doc_type_check": {"status": "pass", "issues_count": 0},
    "blocked_items_check": {"status": "fail", "issues_count": 1}
  },
  "issues": [
    {"issue_id": "R001", "level": "high", "type": "fact_not_grounded", "evidence": "取得显著成效"}
  ],
  "rewrite_instructions": [
    {"priority": "high", "action": "replace", "instruction": "删除无依据拔高表述", "basis": "extract_result"}
  ],
  "review_policy": {"no_body_generation": true, "no_rewrite": true, "no_new_facts": true, "no_rag_call": true}
}
```

> 此示例展示：review 发现 draft 中的"取得显著成效"无依据拔高表述，标记 issue 并给 rewrite 阶段提供具体修订指令。review 不生成正文、不改写正文、不调用 RAG。

## rewrite 二次修订示例

**说明：rewrite 阶段基于 review_result 对 draft_result.markdown_draft 进行定向修订，输出 final_markdown。rewrite 不调用 RAG，不新增事实，不自由重写，只根据 review_result.issues 逐项修订。final_markdown 仍会保留必要的人工确认项。**

### 输入

```json
{
  "draft_result": {
    "markdown_draft": "……取得显著成效，为后续推广奠定了坚实基础……请集团给予专项预算支持。",
    "fact_usage_report": [{"draft_text": "前期筹备工作已完成", "source": "extract_result.fact_items"}],
    "warnings": [{"level": "critical", "type": "missing_field", "message": "预算金额缺失"}]
  },
  "review_result": {
    "pass": false,
    "score": 65,
    "rewrite_required": true,
    "issues": [
      {"issue_id": "R001", "level": "high", "type": "fact_not_grounded", "detail": "取得显著成效无依据"},
      {"issue_id": "R002", "level": "critical", "type": "doc_type_error", "detail": "报告文种中出现请示事项"}
    ],
    "rewrite_instructions": [
      {"priority": "high", "action": "replace", "instruction": "删除无依据拔高表述", "basis": "extract_result"},
      {"priority": "critical", "action": "delete", "instruction": "删除请示事项", "basis": "classify_result.doc_type"}
    ]
  },
  "extract_result": {
    "facts": {"achievements": ["项目已完成前期筹备"]},
    "cannot_infer": [{"field": "项目预期成效"}]
  },
  "classify_result": {"doc_type": "报告", "direction": "上行文"}
}
```

### rewrite 输出（关键片段）

```json
{
  "rewrite_summary": "删除无依据拔高表述，删除报告文种中的请示事项，保留有依据的项目筹备事实。",
  "doc_type": "报告",
  "risk_level": "medium",
  "final_markdown": "……该项目已完成前期筹备，后续推广工作需进一步推进……",
  "revision_report": [
    {
      "revision_id": "REV001",
      "issue_id": "R001",
      "action": "replace",
      "before": "取得显著成效，为后续推广奠定了坚实基础",
      "after": "后续推广工作需进一步推进",
      "reason": "原表述无事实依据，替换为中性表述。",
      "basis": "extract_result"
    },
    {
      "revision_id": "REV002",
      "issue_id": "R002",
      "action": "delete",
      "before": "请集团给予专项预算支持。",
      "after": null,
      "reason": "报告文种不得夹带请示事项，已删除。",
      "basis": "classify_result.doc_type"
    }
  ],
  "resolved_issues": [
    {"issue_id": "R001", "resolution": "替换为中性表述", "basis": "extract_result"},
    {"issue_id": "R002", "resolution": "删除请示事项", "basis": "classify_result.doc_type"}
  ],
  "unresolved_issues": [],
  "remaining_risks": [
    {"level": "medium", "type": "missing_field", "detail": "预算金额缺失", "action": "正式报送前建议补充"}
  ],
  "manual_confirmation_fields": [
    {"field": "项目正式名称", "reason": "用户未提供", "impact": "影响标题准确性", "required_before_final": true},
    {"field": "预算金额", "reason": "用户未提供", "impact": "影响报告完整性", "required_before_final": true}
  ],
  "final_checks": {
    "doc_type_fixed": true,
    "unsupported_facts_removed": true,
    "blocked_items_removed": true,
    "terminology_checked": true,
    "manual_confirmations_preserved": true
  },
  "rewrite_policy": {
    "body_rewritten": true,
    "no_new_facts": true,
    "use_only_extract_facts": true,
    "no_rag_call": true,
    "follow_review_instructions": true,
    "follow_doc_type_rules": true,
    "follow_org_title_dictionary": true
  }
}
```

> 此示例展示：rewrite 根据 review 的两个 issue 分别执行替换和删除操作，每个修改记录 before/after，人工确认项完整保留，rewrite_policy 七项均为 true 证实未新增事实、未调用 RAG、只做了定向修订。

## 回归测试

六阶段 Prompt 管线的完整性、Schema 校验和内容合规性可通过回归测试自动验证。

详细说明和运行方式见：[tests/regression/README.md](tests/regression/README.md)

```bash
cd skills/mango-doc-writer
python tests/regression/run_regression.py
```

## 文档

- [v0.1.2 项目收口说明](docs/mango-doc-writer-v0.1.2-project-brief.md) — 项目交接 / 复盘 / 维护指南
- [用户使用手册](docs/mango-doc-writer-user-guide.md)
- [开发者手册](docs/mango-doc-writer-developer-guide.md)
- [架构说明](docs/mango-doc-writer-architecture.md)
- [Release Notes](docs/mango-doc-writer-release-notes.md)
- [Pipeline 自动化说明](pipeline/README.md)
- [VPS 部署说明](docs/mango-doc-writer-vps-deployment.md) — 环境检查、单篇运行、回归测试、定时任务

## API 自动化运行

```bash
cd skills/mango-doc-writer

# 配置 API key
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 单 case 运行
python scripts/run_case.py tests/cases/002-fake-report-real-request.md

# 全量运行
python scripts/run_all_cases.py
```

## 排版输出说明

六阶段管线输出的 final_markdown 可接入 typeset-engine 生成 DOCX / PDF。

**Markdown 是主交付格式。** DOCX 是公文类增强输出。

- **公文类**（请示/报告/通知/函/通报）：默认同时生成 Markdown + DOCX
- **非公文类**（新闻稿/讲话稿/总结/汇报材料/会议纪要）：默认只生成 Markdown
- 非公文类传入 `--format docx` 时才生成 DOCX

详细说明见：[render/README.md](render/README.md)

```bash
cd skills/mango-doc-writer
# 公文类默认生成 DOCX
python scripts/render_case.py tests/reports/002-fake-report-real-request
# 非公文类默认只生成 Markdown
python scripts/render_case.py tests/reports/001-news
# 非公文类用户明确要求 DOCX
python scripts/render_case.py tests/reports/001-news --format docx
```

---

*最后更新：2026-05-28*
