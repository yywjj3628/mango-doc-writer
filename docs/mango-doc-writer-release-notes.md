# mango-doc-writer Release Notes

## v0.1.3 质量门禁版（2026-05-29）

### 版本主题

Quality Gate — AI 成稿质量评分门禁 + 自动返修闭环。

### 新增能力

1. **后置质量门禁**：rewrite 完成后对 final_markdown 进行六维度评分
2. **六大评分维度**：
   - fact_safety（事实安全）：是否新增了用户未提供的事实
   - doc_type_fit（文种匹配）：标题、结构、格式是否符合文种规范
   - mango_style_fit（芒果风格）：表达是否符合芒果系气质
   - logic_completeness（逻辑完整）：结构是否完整、信息是否交代清楚
   - language_quality（语言质量）：用词是否准确、凝练、正式
   - risk_control（风险控制）：称谓、机构、数据、敏感表达是否稳妥
3. **自动返修闭环**：低于阈值时自动生成返修指令，交给 rewrite 执行定点改进
4. **warn_and_output 机制**：达到最大返修轮次仍不通过时，保留稿件但标记风险，提示人工复核
5. **可配置开关**：QUALITY_GATE_ENABLED / QUALITY_GATE_THRESHOLD / QUALITY_GATE_MAX_ROUNDS 环境变量控制
6. **v0.1.2 兼容**：QUALITY_GATE_ENABLED=false 时完全回退旧流程

### 修改文件摘要

| 文件 | 变更 |
|------|------|
| prompts/07-quality-score.md | 新增：质量门禁评分 Prompt |
| schemas/quality_score.schema.json | 新增：质量门禁输出 Schema |
| pipeline/run_pipeline.py | 修改：接入 quality gate 循环逻辑 |
| pipeline/pipeline_types.py | 修改：PipelineReport 新增 quality_gate_* 字段 |
| tests/regression/test_quality_gate.py | 新增：22 项质量门禁测试 |
| tests/fixtures/quality_score_*.json | 新增：4 个测试 fixtures |
| deploy/env.example | 修改：新增 QUALITY_GATE_* 环境变量 |
| docs/* | 修改：更新架构、开发者手册、用户手册 |

### 测试结果摘要

| 测试 | 结果 |
|------|------|
| 质量门禁测试（22 项） | 22/22 通过 |
| 旧 10 Case 回归测试 | 10/10 通过（真实端到端） |
| Fixtures Schema 校验（4 个） | 4/4 通过 |
| Prompt JSON 示例校验（6 个） | 6/6 通过 |
| Pipeline 代码改动 | 无破坏性变更 |

### 已知限制

1. **质量分不等于事实真伪保证**：quality gate 无法验证事实的真伪，只能检查是否有新增未提供信息
2. **阈值固定**：默认阈值 8 分，可能不适合所有场景，需要根据实际使用调整
3. **返修不保证收敛**：某些问题（如用户素材本身不完整）可能在多次返修后仍无法解决
4. **Prompt 依赖**：评分质量取决于模型对 Prompt 的理解和遵循程度
5. **不覆盖排版质量**：quality gate 只评估文本内容，不评估排版输出

### 人工复核边界

以下情况系统会标记 `human_review_required=true`：

- fact_safety < 8：存在疑似新增事实
- risk_control < 8：存在风险控制隐患
- 达到最大返修轮次后仍存在低于阈值的维度

**重要**：
- 系统不能无人值守正式发稿
- 质量分不等于事实真伪保证
- 涉及领导职务、机构名称、日期、金额、数据、政策表述等仍需人工核对
- quality gate 不调用 RAG、不补充外部事实

---

## v0.1.2 正式版（2026-05-29）

### 发布概述

mango-doc-writer v0.1.2 正式版发布。六阶段 Pipeline 完整闭环，DeepSeek API 自动化已稳定，多 Collection RAG 路由已验证，真实文章端到端测试通过。

### 核心能力

1. **六阶段 Pipeline**：classify → extract → plan → draft → review → rewrite
2. **DeepSeek API 自动化**：deepseek-v4-flash（主）+ deepseek-v4-pro（兜底）
3. **多 Collection RAG 路由**：mango_style_docs + jiuyou_docs，按文种智能分配
4. **mango_style_docs 风格语料库**：148 points，60 篇芒果日志清洗文章
5. **Markdown-first 输出**：最终成稿为标准 Markdown
6. **typeset-engine 集成**：可选 DOCX/PDF/PPTX 渲染
7. **回归测试体系**：10 Case 覆盖全部 10 种文种
8. **Skill Registry 治理**：统一状态来源，Legacy/Disabled 管理
9. **环境变量持久化**：.env + shell 脚本自动加载

### 支持文种（10 种）

新闻稿、通知、请示、报告、函、总结、汇报材料、领导讲话、会议纪要、通报

### 验证结果

| 测试 | 结果 |
|------|------|
| 10 Case Schema 校验 | 48/48 通过 |
| RAG A/B 测试（19.4） | B 组全部优于 A 组 |
| 端到端验证（19.5） | 3 篇真实文章全部成功 |
| 安全检查 | 无污染、无泄漏 |
| 平均质量评分 | 78.7/100 |

### RAG 多 Collection 路由

**新增 mango_style_docs 风格语料库**
- Collection: `mango_style_docs`，148 points，metadata 100% 覆盖
- 来源：芒果日志飞书多维表格，60 篇清洗文章
- 仅作为 style_rag 风格参考，不作为事实来源
- is_fact_safe=false 100%

**RAG 路由按文种分配**
- 新闻稿/活动稿/党建材料：mango_style_docs 4 + jiuyou_docs 2
- 领导讲话：mango_style_docs 3 + jiuyou_docs 3
- 汇报材料/总结：jiuyou_docs 5 + mango_style_docs 1
- 报告/请示/通知/函/会议纪要：jiuyou_docs 6
- openclaw_memory 始终排除

**pipeline_report 增强**
- 新增 rag_collections_used 字段
- 新增 rag_primary_collection / rag_fallback_collection
- 每个 style_reference 记录 collection 来源
- do_not_copy 通用规则

**环境变量外部化**
- RAG_COLLECTION_STYLE / RAG_COLLECTION_BUSINESS / RAG_COLLECTION_DISABLED
- RAG_ENABLE_MULTI_COLLECTION / RAG_TOP_K_TOTAL
- 各文种路由 K 值均可配置

**部署工具增强**
- check_env.py 新增 RAG collection 可达性检查
- healthcheck.py 新增 collection 状态检查

### 未修改
- prompts/*（无变更）
- schemas/*（无变更）
- references/*（无变更）
- pipeline 六阶段主逻辑（无变更）
- Qdrant collection 数据（无变更）
- tests/cases/*（无变更）

---

## v0.1（2026-05-28）

### 已完成功能

**六阶段文案生成闭环**
- 01-classify：文种识别、冲突检测、风险评估
- 02-extract：事实抽取、缺失标记、风险标记
- 03-plan：结构规划、事实绑定、禁止项标记
- 04-draft：正文生成、RAG 风格引用（仅风格）
- 05-review：事实溯源、文种检查、称谓检查、RAG 检查、critical 硬规则
- 06-rewrite：定向修订、最终输出

**支持的文种（10 种）**
- 新闻稿、通知、请示、报告、函、总结、汇报材料、领导讲话、会议纪要、通报

**参考知识库**
- doc-type-rules.md：公文文种规则库
- org-title-dictionary.yaml：机构与领导称谓口径库
- style-rag-policy.md：RAG 使用边界策略

**回归测试**
- 10 个测试用例覆盖全部 10 种文种
- schema 校验（48/48 通过）
- check_report：六阶段完整性 + schema + 策略检查
- check_markdown_claims：观察词扫描 + per-case 特殊规则
- review 硬规则检查（critical issue 联动约束）

**排版输出**
- typeset-engine 接入（HTTP API）
- Markdown-first 输出策略
- 公文类默认 DOCX，非公文类默认 Markdown
- render_report.json 记录排版元数据

### 未完成功能

- API 自动化（智谱 API 接入）
- 批量排版脚本
- PDF 输出（typeset-engine 支持但未测试）
- 自定义排版模板
- 多语言支持
- 用户反馈循环

### 已验证 Case

| Case | 文种 | 结果 |
|------|------|------|
| 001-news | 新闻稿 | ✅ |
| 002-fake-report-real-request | 请示 | ✅ |
| 003-report | 报告 | ✅ |
| 004-notice | 通知 | ✅ |
| 005-meeting-minutes | 会议纪要 | ✅ |
| 006-leader-speech | 领导讲话 | ✅ |
| 007-summary | 总结 | ✅ |
| 008-letter | 函 | ✅ |
| 009-rag-pollution | 新闻稿 | ✅ |
| 010-terminology-risk | 汇报材料 | ✅ |

### 已知限制

1. **未接 API**：六阶段仍需手动执行（Prompt 已就绪，待接入智谱 API）
2. **RAG 覆盖有限**：style_rag 依赖已有历史文稿，新领域可能风格参考不足
3. **称谓库不完整**：org-title-dictionary.yaml 需要持续更新
4. **PDF 未验证**：typeset-engine 支持 PDF 但未实际测试
5. **子代理生成质量**：子代理对 review 硬规则理解不够准确，需要人工校验

### 下一步建议

1. **接入智谱 API**：用 Python 脚本自动化六阶段调用
2. **扩展测试用例**：增加更多边界场景（如长文本、多文种混合）
3. **完善称谓库**：补充更多芒果系机构和领导称谓
4. **PDF 输出验证**：测试 typeset-engine 的 PDF 生成质量
5. **用户反馈收集**：在实际使用中收集改进意见

### 不建议立即做的事情

1. ❌ 不建议修改 prompts（当前版本已验证 10 个 case）
2. ❌ 不建议修改 schemas（会导致已有输出不兼容）
3. ❌ 不建议重构 typeset-engine（当前版本满足需求）
4. ❌ 不建议增加新文种（先巩固现有 10 种）
5. ❌ 不建议接入更多 RAG 来源（先确保现有 RAG 使用边界正确）
