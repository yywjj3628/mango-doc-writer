# mango-doc-writer v0.1.2 项目收口说明

> **文档定位**：项目交接 / 复盘 / 后续维护说明。
> **不是**用户手册、开发教程。
> **更新时间**：2026-05-29
> **作者**：卡乐比（OpenClaw 助手，由 MR Yin 指挥完成）

---

## 1. 项目一句话说明

**mango-doc-writer** 是一套面向湖南广电 / 芒果体系 / 电广传媒相关文案场景的 **OpenClaw Skill 文案生产系统**，用于将用户初稿或素材转化为符合广电系统文风、公文规范、新闻稿表达和芒果体系风格的 `final_markdown` 成稿。

关键定性：

- **是 OpenClaw Skill**——通过 SKILL.md 定义触发条件，在 OpenClaw 对话中自动识别并调用，不是独立 CLI 工具。
- **不是单 Prompt**——由六个串联阶段组成完整管线，每阶段有独立 Prompt、独立 JSON Schema、独立职责边界。
- **是六阶段 Pipeline**——classify → extract → plan → draft → review → rewrite，每阶段输出经 jsonschema 校验。
- **RAG 只用于风格参考**——RAG 检索结果（style_rag）仅参与 draft 阶段作为句式/文风参考，不作为事实来源，不决定文种，不补充领导职务/数据/出席信息。
- **事实以用户输入和 extract_result 为准**——所有正文中的事实必须可溯源到用户提供素材或 extract 阶段抽取结果。
- **final_markdown 是主输出**——Markdown 为第一交付格式，所有文种默认输出 final_markdown。
- **DOCX 是可选增强输出**——公文类（请示/报告/通知/函/通报）默认同时生成 DOCX，非公文类需用户显式要求才生成。

---

## 2. 当前版本状态

### 版本号

**mango-doc-writer v0.1.2**

### 版本定位

| 属性 | 描述 |
|------|------|
| 定性 | 内部正式试用版 |
| 生产就绪度 | 小规模生产可用 |
| RAG 能力 | 多 Collection 路由增强正式版 |
| 人工复核要求 | **仍需人工复核关键事实和称谓** |

### 当前建议状态

> ✅ 可以用于真实工作流
> ❌ 不能无人值守正式发稿

### 必须人工复核的项目

以下字段在任何场景下都必须由人工核对后才可正式使用：

- 领导职务（是否与最新口径一致）
- 主送单位（机构全称是否准确）
- 落款日期（是否与实际报送日期一致）
- 预算金额（是否与审批文件一致）
- 会议时间地点（是否与实际安排一致）
- 出席人员（是否与实际参会名单一致）
- 具体经营数据（是否与财务/业务口径一致）
- 政策表述（是否与最新政策文件一致）
- 涉及上级单位的称谓（是否与最新组织架构一致）

---

## 3. 系统总体架构

### 数据流简图

```
OpenClaw 用户对话输入
  │
  ▼
input_parser（解析 JSON / 自然语言 → PipelineInput）
  │
  ▼
run_pipeline（六阶段串联执行）
  ├── 01 classify    → 判断文种 / 行文方向 / 风险等级 / 文种冲突
  ├── 02 extract     → 抽取用户提供的事实（不补充外部事实）
  ├── 03 plan        → 根据文种规则 + 事实规划结构和标题
  ├── 04 draft       → 生成正文初稿（调用 style_rag 风格参考）
  ├── 05 review      → 审查初稿（事实溯源 / RAG 污染 / 称谓 / 文种规则）
  └── 06 rewrite     → 定点修订 → 输出 final_markdown
  │
  ▼
output_formatter（格式化 pipeline_report + 结果摘要）
  │
  ▼
final_markdown.md    ← 主输出
  │
  ▼（可选）
render_pipeline     → typeset-engine → DOCX / PDF
```

### 外部依赖

| 依赖 | 地址 | 用途 | 必要性 |
|------|------|------|--------|
| DeepSeek API | `https://api.deepseek.com`（可通过 BASE_URL 覆盖） | 六阶段 LLM 调用 | **必需** |
| Qdrant | Docker 容器 | 向量存储 | **必需**（RAG 底层） |
| RAG search 服务 | `http://localhost:8000/search` | 风格参考检索 | **必需**（draft 阶段） |
| typeset-engine | `http://localhost:9090` | Markdown → DOCX/PDF 排版 | 可选 |
| VPS 环境变量 | `.env` 或 `/etc/mango-doc-writer.env` | API Key、RAG 配置 | **必需** |
| OpenClaw Skill 入口 | `entry/openclaw_entry.md` + `SKILL.md` | 对话触发与调用路由 | **必需** |

---

## 4. 六阶段 Pipeline 说明

### 4.1 classify（文种识别）

**职责**：

- 判断文种（10+ 类：新闻稿/活动稿/宣传稿/司情新闻稿/领导讲话/汇报材料/总结/报告/请示/通知/函/通报/会议纪要/党建材料/学习稿）
- 判断行文方向（上行文/下行文/平行文/对内/对外）
- 判断风险等级（low / medium / high / critical）
- 识别用户指定文种与真实内容是否冲突

**典型能力**：

用户说"写一份报告"，但内容实际包含请求专项预算支持——classify 识别为"请示"，标记 `conflict_detected: true`，给出 `recommended_action: "建议改为请示"`，并列出 `possible_confusions` 供人工选择。

**输出 Schema**：`schemas/classify.schema.json`

---

### 4.2 extract（事实抽取）

**职责**：

- 只抽取用户提供的事实
- 不补充任何外部事实
- 抽取维度：时间、地点、机构、人物、产品、项目、数据、成就、问题、请求、后续事项等

**阶段 19 已补强**：

- 后续工作事项抽取
- "做好半年报准备工作"类隐含工作要求
- 报送事项 / 时间节点
- 工作要求类指令

**输出 Schema**：`schemas/extract.schema.json`

---

### 4.3 plan（结构规划）

**职责**：

- 根据文种规则和事实抽取结果规划成稿结构
- 生成标题建议（含标题置信度和风险提示）
- 生成段落安排（每个 section 绑定 extract 事实来源）
- 标记缺失字段和人工确认项
- 生成 `draft_directives`（must_use_facts / must_avoid）

**输出 Schema**：`schemas/plan.schema.json`

---

### 4.4 draft（初稿生成）

**职责**：

- 生成正文初稿 Markdown
- 调用 style_rag 获取风格参考（仅此阶段调用 RAG）
- 只使用 extract 中的事实，每个事实在 `fact_usage_report` 中溯源
- RAG 只用于风格和句式，不作为事实来源
- 如 RAG 不可用，不阻塞 pipeline，使用空 style_references 继续生成

**关键约束**：

```
draft_policy:
  body_generated: true
  no_new_facts: true
  rag_used_for_style_only: true
```

**输出 Schema**：`schemas/draft.schema.json`

---

### 4.5 review（质检审查）

**职责**：

- 审查初稿（不生成正文、不重写正文、不调用 RAG）
- 检查事实新增（与 extract_result 逐一比对）
- 检查 RAG 污染（旧稿领导职务/数据/成果是否渗入新稿）
- 检查称谓风险（机构/领导/产品名称是否准确）
- 检查文种错误（是否混用报告/请示等易混文种）
- 检查报告/请示混用
- 检查是否需要 rewrite（给出 rewrite_required + rewrite_instructions）
- 输出结构化质检报告

**输出 Schema**：`schemas/review.schema.json`

---

### 4.6 rewrite（二次修订）

**职责**：

- 根据 review_result 定点修订 draft_result.markdown_draft
- 删除无依据事实（事实新增 issue）
- 删除 RAG 污染（style leakage issue）
- 保留人工确认项（manual_confirmation_fields）
- 输出 final_markdown
- 每个修订记录 before/after/action/reason/basis

**关键约束**：

```
rewrite_policy:
  body_rewritten: true
  no_new_facts: true
  use_only_extract_facts: true
  no_rag_call: true
  follow_review_instructions: true
  follow_doc_type_rules: true
  follow_org_title_dictionary: true
```

**输出 Schema**：`schemas/rewrite.schema.json`

---

## 5. 核心目录说明

```
skills/mango-doc-writer/
├── SKILL.md                              # OpenClaw Skill 定义（触发条件、流程）
├── README.md                             # 项目说明（含示例）
├── .env                                  # 环境变量（API Key 等，不入 Git）
├── .gitignore
│
├── prompts/                              # 六阶段 Prompt（Markdown 格式）
│   ├── 01-classify.md
│   ├── 02-extract.md
│   ├── 03-plan.md
│   ├── 04-draft.md
│   ├── 05-review.md
│   └── 06-rewrite.md
│
├── schemas/                              # 六阶段 JSON Schema（输出格式约束）
│   ├── classify.schema.json
│   ├── extract.schema.json
│   ├── plan.schema.json
│   ├── draft.schema.json
│   ├── review.schema.json
│   └── rewrite.schema.json
│
├── references/                           # 知识库 / 规则库
│   ├── doc-type-rules.md                 # 10+ 文种规则（结构/禁忌/风格强度）
│   ├── org-title-dictionary.yaml         # 机构称谓/领导职务/产品名/禁用称谓
│   ├── style-rag-policy.md                # RAG 定位与使用边界
│   ├── mango-style-guide.md              # 芒果风格指南
│   ├── output-templates.md               # 输出模板
│   └── forbidden-expressions.md         # 禁用表达列表
│
├── pipeline/                             # 自动化管线核心
│   ├── run_pipeline.py                   # 六阶段串联主入口
│   ├── model_client.py                   # DeepSeek API 调用客户端
│   ├── model_runner.py                   # 模型调用器（LLM 接口层）
│   ├── rag_client.py                     # 多 Collection RAG 检索客户端
│   ├── schema_loader.py                  # JSON Schema 加载与校验
│   ├── schema_prompt.py                  # Schema Guard 注入
│   ├── input_parser.py                   # 输入解析器
│   ├── output_formatter.py               # 输出格式化
│   └── pipeline_types.py                 # 类型定义
│
├── render/                               # Markdown → DOCX/PDF 可选排版层
│   ├── render_pipeline.py
│   ├── render_types.py
│   └── doc_type_mapping.yaml
│
├── scripts/                              # 运行脚本
│   ├── run_input.py                      # 真实输入运行入口（支持 stdin/文件）
│   ├── run_case.py                       # 单 case 运行
│   ├── run_all_cases.py                  # 全量 case 运行
│   ├── render_case.py                    # 单 case 排版
│   ├── ingest_mango_style_docs.py        # 芒果系语料入库
│   ├── audit_mango_style_docs.py         # 语料库审计
│   ├── ab_test.py                        # A/B 测试
│   └── ab_test_rag_only.py              # RAG A/B 测试
│
├── tests/
│   ├── cases/                            # 10 个标准测试 case（001-010）
│   ├── regression/                       # 回归测试工具
│   ├── reports/                          # 阶段报告和测试报告
│   └── TESTING_GUIDE.md
│
├── corpus/
│   └── mango_style_docs/
│       └── cleaned/                      # 60 篇芒果系风格语料（清洗后）
│
├── deploy/                               # VPS 部署相关
│   ├── check_env.py                      # 环境变量检查
│   ├── healthcheck.py                    # 系统健康检查
│   ├── env.example                       # 环境变量模板
│   ├── run_single.sh                     # 运行单篇测试
│   ├── run_regression.sh                 # 全量回归测试
│   ├── logrotate.example                 # 日志轮转配置
│   └── systemd/                          # systemd 服务/定时器
│
├── entry/                                # OpenClaw Skill 入口
│   ├── openclaw_entry.md                 # 入口说明文档
│   ├── input_template.json               # 输入模板
│   └── README.md
│
├── docs/                                 # 项目文档
│   ├── mango-doc-writer-user-guide.md
│   ├── mango-doc-writer-developer-guide.md
│   ├── mango-doc-writer-architecture.md
│   ├── mango-doc-writer-release-notes.md
│   ├── mango-doc-writer-vps-deployment.md
│   ├── mango-doc-writer-openclaw-skill-guide.md
│   ├── skill-inventory-report.md
│   └── mango-doc-writer-v0.1.2-project-brief.md  ← 本文件
│
├── outputs/                              # 真实输入输出结果
└── logs/                                 # 运行日志
```

---

## 6. 当前知识库 / 规则库说明

### 6.1 doc-type-rules.md

**作用**：10+ 类文种规则库。

**覆盖文种**：新闻稿、活动稿、宣传稿、司情新闻稿、领导讲话、汇报材料、总结、报告、请示、通知、函、通报、会议纪要、党建材料、学习稿。

**每个文种包含**：适用场景、行文方向、标题格式、标准结构（段落数量和排列）、语言风格强度、禁止事项、与其他文种的区分规则。

**核心价值**：classify 后加载对应文种规则，约束 draft 和 review 行为。这是硬约束来源，不由 RAG 替代。

**易混文种处理**：

- 请示 vs 报告：请示请求上级批准/支持/拨款，报告只汇报情况
- 新闻稿 vs 司情新闻稿：对外发布 vs 系统内通报
- 汇报材料 vs 总结：汇报材料有明确主送对象，总结面向组织内部

---

### 6.2 org-title-dictionary.yaml

**作用**：机构称谓、领导职务、产品/平台名称、战略词、禁用称谓的统一口径库。

**包含**：

- `organizations`：湖南广播影视集团（台）、电广传媒、久之润等机构全称/简称
- `leaders`：领导职务（优先级：用户指定 > 旧稿继承 > 口径库）
- `products`：芒果 TV、劲舞团等产品/平台名称
- `strategies`：五新战略、双前锋、系统性变革等战略表达
- `forbidden_titles`：禁用称谓列表
- `conflict_resolution`：冲突处理规则

**阶段 19 已补充**：

- `jiuyou_platform` / `久游网` 系列条目

**称谓来源优先级**：

1. 用户明确指定的当次输入（最高信任）
2. 现有 60 篇芒果系旧稿 / 老板亲自把关稿件
3. mango-writer style-guide / RAG 语料
4. doc-type-rules.md（仅文种规则）
5. ❌ 模型自身知识（禁止）

---

### 6.3 style-rag-policy.md

**作用**：定义 RAG 在 mango-doc-writer 中的定位与使用边界。

**核心规则**：

- RAG 定位为 **style_rag**（风格案例检索层）
- **禁止** RAG 补充事实、决定文种、决定主送单位、决定领导职务、决定机构全称
- **禁止** 自动补充领导出席、领导评价、数据、获奖信息
- RAG 只用于借鉴文风、标题风格、开头句式、段落节奏、战略表达、同类文种案例
- 只在 draft 阶段调用一次

---

### 6.4 mango_style_docs

**作用**：新建的高质量芒果系风格 RAG Collection。

**统计数据**：

| 指标 | 值 |
|------|-----|
| 文章数 | 60 篇 |
| chunks 数 | 148 |
| metadata 覆盖率 | 100% |
| `is_fact_safe` | false（100%，不作为事实来源） |

**内容来源**：芒果日志等公开渠道采集的湖南广电/芒果系官方新闻稿、活动稿、讲话稿等。

**适用场景**：新闻稿、活动稿、宣传稿、司情新闻稿、领导讲话等需要强芒果文风的文种。

---

### 6.5 jiuyou_docs

**作用**：企业材料 / 电广传媒 / 久游 / 公文补充库。

**适用场景**：公文（请示/报告/通知/函/会议纪要）、汇报材料、总结等需要正式公文风格的文种。此库包含真实的企业经营管理文档、制度文件、会议纪要等。

**特点**：公文、汇报材料、经营材料主要使用此库。

---

### 6.6 openclaw_memory

**作用**：OpenClaw 记忆日志 Collection。

**状态**：**禁止参与 mango-doc-writer RAG**。`RAG_COLLECTION_DISABLED` 默认设为 `openclaw_memory`，rag_client 不会查询此库。

---

## 7. RAG 路由说明

### 当前路由策略

RAG 检索已经**不是单库硬编码**，而是按文种动态路由到不同 Collection，可调节各文种的 top_k 分配。

| 文种类别 | 主 Collection | 主 top_k | 辅 Collection | 辅 top_k |
|----------|---------------|---------|---------------|---------|
| 新闻稿 / 活动稿 / 宣传稿 / 司情新闻稿 / 党建材料 / 学习稿 | mango_style_docs | 4 | jiuyou_docs | 2 |
| 领导讲话 | mango_style_docs | 3 | jiuyou_docs | 3 |
| 通报 | jiuyou_docs | 5 | mango_style_docs | 1 |
| 汇报材料 / 总结 | jiuyou_docs | 5 | mango_style_docs | 1 |
| 报告 / 请示 / 通知 / 函 / 会议纪要 | jiuyou_docs | 6 | — | — |
| openclaw_memory | **禁用** | — | — | — |

### 路由实现

路由规则定义在 `pipeline/rag_client.py` 的 `ROUTING_TABLE` 字典中。可通过环境变量调整各文种的 top_k 分配（如 `RAG_NEWS_STYLE_K`、`RAG_SPEECH_BUSINESS_K` 等），无需修改代码。

### 路由结果记录

RAG 路由结果会写入 `pipeline_report.json`，包含以下字段：

- `rag_status`：RAG 调用状态（success / skipped / failed）
- `rag_collections_used`：本次查询使用的 Collection 列表
- `rag_primary_collection`：主 Collection 名称
- `rag_fallback_collection`：辅 Collection 名称（如有）
- `style_references_count`：检索到的风格参考条数
- `rag_sources`：每条参考的来源 chunk 信息

---

## 8. 模型与环境变量说明

### 默认模型

- **主模型**：`deepseek-v4-flash`（控制成本，适合全量回归和日常使用）
- **Fallback 模型**：`deepseek-v4-pro`（仅在主模型失败重试时使用）

### 配置来源

优先级：`/etc/mango-doc-writer.env` > 项目目录 `.env` > 环境变量

### 关键环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **必需**，DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 端点 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 主模型 |
| `DEEPSEEK_FALLBACK_MODEL` | `deepseek-v4-pro` | 兜底模型 |
| `DEEPSEEK_ENABLE_FALLBACK` | `true` | 是否启用兜底 |
| `DEEPSEEK_TIMEOUT` | `120` | 调用超时（秒） |
| `DEEPSEEK_MAX_RETRIES` | `2` | 最大重试次数 |
| `RAG_BASE_URL` | `http://localhost:8000/search` | RAG 检索端点 |
| `RAG_ENABLE_MULTI_COLLECTION` | `true` | 是否启用多 Collection 路由 |
| `RAG_TOP_K_TOTAL` | `6` | 总返回上限 |
| `RAG_COLLECTION_STYLE` | `mango_style_docs` | 风格 Collection |
| `RAG_COLLECTION_BUSINESS` | `jiuyou_docs` | 业务 Collection |
| `RAG_COLLECTION_DISABLED` | `openclaw_memory` | 禁用 Collection |
| `TYPESET_ENGINE_ENABLED` | `true` | 是否启用排版引擎 |
| `TYPESET_ENGINE_BASE_URL` | `http://localhost:9090` | 排版引擎端点 |

### 安全规则

- **API Key 不得写入 Git**——`.env` 已加入 `.gitignore`
- `check_env.py` 只打印 `present / missing` 和 key 长度，**禁止打印真实 API Key**
- `env.example` 是环境变量模板，不含真实 Key

---

## 9. 输出策略

### 主输出

`final_markdown.md`——Markdown 格式的最终成稿，所有文种默认生成。

### 可选输出

DOCX / PDF——通过 typeset-engine 排版生成。

### Markdown-first 策略

- 所有文种默认输出 `final_markdown`
- 公文类（请示/报告/通知/函/通报）可选 DOCX
- 新闻稿、领导讲话、汇报材料默认只输出 Markdown
- typeset-engine 只负责排版，**不参与写作**
- 排版失败不影响 `final_markdown` 的生成和可用性

---

## 10. Skill 治理状态

阶段 20 / 20.1 已完成 Skill 治理。

### 当前 registry（skills/registry.yaml）

| 状态 | Skill | 说明 |
|------|-------|------|
| **production** | mango-doc-writer | ✅ 当前主力 |
| production | typeset-engine | 排版引擎 |
| production | jiuyou-weekly-writer | 久游周报 |
| production | mango-writer | ⚠️ 已被 mango-doc-writer 替代 |
| legacy | mango-writer | 历史版本，保留但不再新增功能 |
| legacy | jiuyou-weekly-report | 历史版本 |
| legacy | anthropic-docx/pdf/pptx/xlsx | 历史版本 |
| disabled | deer-flow / deerflow-dispatcher | 已禁用 |

### ⚠️ 重要

**mango-writer 已被 mango-doc-writer 替代。** 后续不要再调用 mango-writer 做芒果系文案。所有芒果系文案生产应统一通过 mango-doc-writer Skill。

---

## 11. 已完成阶段摘要

| 阶段 | 内容 |
|------|------|
| 1-4 | Skill 骨架搭建、文种规则库（doc-type-rules.md）、口径库（org-title-dictionary.yaml）、RAG 策略（style-rag-policy.md） |
| 5-10 | 六阶段 Prompt 编写（classify/extract/plan/draft/review/rewrite）+ JSON Schema |
| 11-12 | 10 个标准测试 case 编写 + 回归测试工具 |
| 13-14 | Markdown-first 策略确立、文档整理 |
| 15 | DeepSeek API 自动化接入（model_client.py） |
| 16 | VPS 固化部署（环境变量、健康检查、运行脚本） |
| 17 | OpenClaw Skill 入口固化（SKILL.md + entry/） |
| 18 | 真实文章试跑（平均分约 85） |
| 19 | 轻量微调、mango_style_docs 语料库（60篇/148 chunks）、RAG 多 Collection 路由、端到端验证（平均分 78.7） |
| 20 | Skill 治理（registry 整理） |
| 20.1 | registry 标记 + v0.1.2 发布准备 |
| 21 | 项目收口说明文档（本文件） |

---

## 12. 已验证结果

### 10 Case 回归测试

- **结果**：10/10 通过
- **覆盖文种**：新闻稿、报告、通知、会议纪要、领导讲话、总结、函、RAG 污染风险、称谓风险
- **Schema 校验**：全部通过 jsonschema.validate

### 真实文章试跑（阶段 18）

- **平均分**：约 85
- **事实新增**：零
- **文种错误**：零
- **RAG 污染**：零

### 端到端 RAG 路由验证（阶段 19.5）

| 测试项 | 结果 |
|--------|------|
| 新闻稿 | ✅ success |
| 领导讲话 | ✅ success |
| 请示 | ✅ success |
| RAG 路由 | ✅ 正常（多 Collection 按文种路由） |
| 安全检查 | ✅ 全通过 |
| 平均分 | 78.7 |

### 002 / 009 端到端验证（阶段 19）

- 端到端完整跑通
- final_markdown 正常保存
- API Key 无泄漏
- RAG 污染防线正常

---

## 13. 当前限制

**如实记录**，不回避：

1. **mango_style_docs 语料规模有限**——目前只有 60 篇文章、148 chunks，对复杂文风场景覆盖不够充分
2. **汇报材料/请示/报告/通知/函/会议纪要语料不足**——这些文种主要依赖 jiuyou_docs，缺少芒果系风格参考
3. **领导讲话语料偏少**——风格参考覆盖面有限
4. **文风提升主要依赖后续语料扩充**——当前 pipeline 架构已稳定，提升空间在语料规模和质量
5. **无真正全自动自学习能力**——目前是人工维护知识库 + RAG 检索 + 回归验证
6. **新领导职务和机构口径不能自动写入**——需人工更新 org-title-dictionary.yaml
7. **仍需人工复核关键事实**——任何涉及职务/数据/日期/金额的字段
8. **不建议无人值守正式发稿**——系统生成内容必须经过人工审核

---

## 14. 后续路线

### v0.2.0 主题：语料工程建设

| 优先级 | 内容 | 说明 |
|--------|------|------|
| **P0** | 持续补充 mango_style_docs | 扩大新闻稿/活动稿/讲话稿语料，提升 RAG 覆盖 |
| **P1** | 补电广传媒通知、领导讲话、司情新闻稿 | 当前缺失的高频文种 |
| **P2** | 补汇报材料/请示/报告/通知/函/会议纪要 | 公文类语料 |
| **P3** | 建立语料入库流水线 | 自动化采集 → 清洗 → 分块 → 入库 |
| **P4** | 建立候选知识提炼模块 | 从新语料中自动提取机构/职务/战略词供人工审核 |
| **P5** | 建立人工确认后写入规则库的机制 | 审核通过的称谓/规则自动更新 yaml/md |
| **P6** | 扩大真实文章测试到 20-50 篇 | 覆盖更多文种和边缘场景 |

### 不建议近期做

- ❌ Web API / REST 接口（当前通过 OpenClaw Skill + CLI 足够）
- ❌ 大规模重构 pipeline（架构已稳定，六阶段闭环经充分验证）
- ❌ 全自动自学习（人工维护 + 审核仍是必要环节）
- ❌ 自动把生成稿回灌 RAG（会导致事实循环污染）
- ❌ 无审核自动更新领导职务（称谓变更必须经人工确认）

---

## 15. 常用命令

```bash
cd skills/mango-doc-writer

# 环境检查（检查 API Key、RAG 服务等）
python deploy/check_env.py

# 健康检查（检查依赖服务可用性）
python deploy/healthcheck.py

# 运行单篇测试 case
bash deploy/run_single.sh tests/cases/002-fake-report-real-request.md

# 运行全量回归测试（10 cases）
bash deploy/run_regression.sh

# 真实输入运行
python scripts/run_input.py --input inputs/example.json --stdout
# 或通过 stdin
echo '{"requirement":"...","draft":"..."}' | python scripts/run_input.py --stdin

# 芒果系语料入库
python scripts/ingest_mango_style_docs.py --collection mango_style_docs

# 审计语料库
python scripts/audit_mango_style_docs.py
```

---

## 16. 常见故障

### missing_api_key

**现象**：pipeline 启动报错 `EnvironmentError: 未检测到 DEEPSEEK_API_KEY 环境变量`

**原因**：DEEPSEEK_API_KEY 没有在 `.env` 或 `/etc/mango-doc-writer.env` 中配置，或文件格式错误。

**处理**：

```bash
# 检查环境变量
python deploy/check_env.py
# 确认 .env 文件存在且格式正确（无空格、无多余引号）
cat .env | grep DEEPSEEK_API_KEY
```

---

### final_markdown 未生成

**现象**：pipeline 完成但 outputs 目录下没有 `final_markdown.md`

**原因**：rewrite 阶段 `final_markdown` 字段为空，或 pipeline 保存阶段 bug。

**处理**：检查 rewrite 阶段的 `rewrite_result.json` 和 `pipeline_report.json`，查看 rewrite 阶段是否正常完成。

---

### RAG failed / RAG skipped

**现象**：`pipeline_report.json` 中 `rag_status` 为 `failed` 或 `skipped`

**原因**：

- `http://localhost:8000/search` 不可用（RAG 服务未启动）
- Qdrant 容器未运行或对应 Collection 不存在
- 网络不通

**处理**：

```bash
# 检查 RAG 服务
curl http://localhost:8000/search -d '{"question":"test","collection":"mango_style_docs","top_k":1}'
# 检查 Qdrant
curl http://localhost:6333/collections/mango_style_docs
```

> RAG 不可用时 draft 阶段仍会继续执行（使用空 style_references），不会阻塞 pipeline。

---

### schema_validation_error

**现象**：某阶段输出未通过 jsonschema.validate

**原因**：模型输出不符合 JSON Schema 约束（缺少必填字段、类型错误等）。

**处理**：

1. 查看 `pipeline_report.json` 中的 `failed_stage`
2. 查看对应阶段的 `debug_output_path` 中的原始模型输出
3. 查看 `sanitizer_report`（如有）
4. 常见原因：模型输出格式不稳定，可检查 prompt 中的 schema guard 是否完整

---

### RAG 污染

**现象**：final_markdown 中出现用户未提供的领导职务、历史数据、旧稿成果。

**原因**：RAG 检索到的旧稿事实渗入正文。

**处理**：

1. 检查 `review_result.json` 中的 RAG 污染 issue
2. 检查 `rewrite_result.json` 中的修订记录
3. 检查 `rag_sources` 和 `do_not_copy` 列表
4. 如果 review 未检出，可能需要调整 `style-rag-policy.md` 或 `05-review.md` 的检查规则

---

## 17. 后续维护原则

> **遇到问题不要先改 Prompt。** 优先按以下判断路由到对应文件。

| 问题类型 | 应该检查/修改的文件 | 不应该动 |
|----------|---------------------|----------|
| 称谓错误 | `references/org-title-dictionary.yaml` | Prompt |
| 文种结构错误 | `references/doc-type-rules.md` | Pipeline |
| 文风不像芒果系 | `corpus/mango_style_docs/`（补充语料） | Prompt |
| 事实漏抽 | `prompts/02-extract.md` | 其他 Prompt |
| RAG 污染 | `references/style-rag-policy.md` → `prompts/05-review.md` → `prompts/06-rewrite.md` | Pipeline 逻辑 |
| 输出格式不好看 | `pipeline/output_formatter.py` → `render/` | Prompt |
| DOCX 排版问题 | typeset-engine（独立 Skill） | mango-doc-writer |
| 调用错 Skill | `skills/registry.yaml` → `SKILL.md` | — |

---

## 18. 最终结论

**mango-doc-writer v0.1.2 已达到内部正式试用 / 小规模生产可用状态。**

系统在以下方面已充分验证：

- ✅ 六阶段 Pipeline 完整闭环（classify → extract → plan → draft → review → rewrite）
- ✅ 10 Case 回归测试全通过
- ✅ 多 Collection RAG 路由工作正常
- ✅ RAG 污染防线有效（零事实新增、零污染）
- ✅ 文种冲突识别准确
- ✅ 称谓/机构口径可控
- ✅ API Key 安全无泄漏
- ✅ VPS 部署固化，环境变量管理规范
- ✅ OpenClaw Skill 入口已固化

**后续主要提升空间不在 Pipeline，而在语料规模、语料质量、口径库厚度和真实文章反馈闭环。**

建议进入 **v0.2.0 语料工程建设阶段**，以 P0-P3 为优先级推进。

---

*文档完成时间：2026-05-29*
*对应版本：mango-doc-writer v0.1.2*
*文档类型：项目收口说明（交接 / 复盘 / 维护指南）*
