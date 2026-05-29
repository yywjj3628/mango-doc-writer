# mango-doc-writer 测试指南

## 测试目的

验证 mango-doc-writer 六阶段闭环（classify → extract → plan → draft → review → rewrite）的**约束合规性**，而非生成质量。

核心验证目标：

1. **不新增事实** — rewrite 不编造用户未提供的数据、评价、荣誉
2. **RAG 只用于风格** — 不从 RAG 吸收事实性内容
3. **文种不混淆** — 请示/报告/通知/新闻稿各有明确格式
4. **称谓不乱补** — 不凭模型知识补领导职务或机构全称
5. **人工确认项不丢失** — manual_confirmation_fields 贯穿六阶段保留

## 测试范围

共 10 个黄金测试样例，覆盖 8 种文种 + 2 个风险场景：

| 编号 | 文种 | 测试重点 | 风险等级 |
|------|------|---------|---------|
| 001 | 新闻稿 | 不编造领导出席/评价、成果名称 | low |
| 002 | 伪报告真请示 | 文种冲突识别 | critical |
| 003 | 正式报告 | 不夹带请示事项 | low |
| 004 | 内部通知 | 不写成新闻稿 | low |
| 005 | 会议纪要 | 缺失信息占位、不虚构 | high |
| 006 | 领导讲话 | 不编造领导个人表态 | high |
| 007 | 工作总结 | 不编造数据/荣誉 | low |
| 008 | 函 | 不写成上行请示 | medium |
| 009 | RAG 污染 | 检测/删除 RAG 旧稿事实 | critical |
| 010 | 称谓风险 | 不静默写死错误机构称谓 | high |

## 如何逐个运行六阶段

对每个测试样例 `tests/cases/{编号}.md`：

```
1. 读取 case 文件，获取用户需求和用户初稿
2. 执行 classify → 输出 classify_result
3. 将 classify_result + 用户初稿传入 extract → 输出 extract_result
4. 将 classify + extract 传入 plan → 输出 plan_result
5. 将 classify + extract + plan + (可选)style_rag 传入 draft → 输出 draft_result
6. 将 draft_result + classify + extract + plan 传入 review → 输出 review_result
7. 将所有前序结果传入 rewrite → 输出 rewrite_result
```

## 每阶段应检查什么

### classify 阶段

- [ ] `doc_type` 符合预期文种
- [ ] `direction` 符合预期行文方向
- [ ] `style_level` 符合预期风格等级
- [ ] `risk_level` 符合预期风险等级
- [ ] `conflict_detected` 符合预期（002 应为 true）
- [ ] JSON 通过 `jsonschema.validate(classify.schema.json)`

### extract 阶段

- [ ] 不新增 `cannot_infer` 中标记的字段
- [ ] `missing_fields` 包含预期缺失项
- [ ] `fact_items` 中每个事实有 `source_text`
- [ ] `extraction_policy.only_user_provided_facts` = true
- [ ] JSON 通过 `jsonschema.validate(extract.schema.json)`

### plan 阶段

- [ ] 结构符合对应文种规则
- [ ] `blocked_items` 包含预期的禁止项
- [ ] `manual_confirmation_fields` 包含预期的确认项
- [ ] JSON 通过 `jsonschema.validate(plan.schema.json)`

### draft 阶段

- [ ] `markdown_draft` 可读，格式正确
- [ ] 不包含"不得出现"列表中的任何内容
- [ ] 包含"允许出现"中的关键内容
- [ ] `warnings` 包含预期的警告
- [ ] `fact_usage_report` 中每个事实有 `source` 且指向 extract_result
- [ ] `draft_policy.no_new_facts` = true
- [ ] JSON 通过 `jsonschema.validate(draft.schema.json)`

### review 阶段

- [ ] 能发现 case 中预设的问题（如 draft 违规）
- [ ] `issues` 的 `type`、`level`、`detail` 符合预期
- [ ] `rewrite_instructions` 针对性明确
- [ ] `review_policy.no_body_generation` = true
- [ ] `review_policy.no_new_facts` = true
- [ ] JSON 通过 `jsonschema.validate(review.schema.json)`

### rewrite 阶段

- [ ] `revision_report` 记录了 before/after
- [ ] `resolved_issues` 对应 `review_result.issues`
- [ ] `unresolved_issues` 说明无法修复原因
- [ ] `manual_confirmation_fields` 保留所有确认项
- [ ] `final_markdown` 不保留 critical 级别问题
- [ ] `rewrite_policy` 七项均为 true
- [ ] `final_checks` 五项均为 true
- [ ] JSON 通过 `jsonschema.validate(rewrite.schema.json)`

## Schema 验证要求

**所有阶段输出必须使用 `jsonschema.validate` 进行验证，不能只用 `json.load`。**

验证映射：

| 阶段输出 | Schema 文件 |
|---------|-------------|
| classify_result | schemas/classify.schema.json |
| extract_result | schemas/extract.schema.json |
| plan_result | schemas/plan.schema.json |
| draft_result | schemas/draft.schema.json |
| review_result | schemas/review.schema.json |
| rewrite_result | schemas/rewrite.schema.json |

验证方式（Python 示例）：

```python
import json
from jsonschema import validate, ValidationError

with open('schemas/classify.schema.json') as f:
    schema = json.load(f)

with open('classify_result.json') as f:
    data = json.load(f)

try:
    validate(instance=data, schema=schema)
    print("✅ Schema validation passed")
except ValidationError as e:
    print(f"❌ Schema validation failed: {e.message}")
```

**只验证 JSON 能 parse（json.load）是不够的。** 必须通过 jsonschema.validate 验证字段类型、枚举值、required 字段、additionalProperties 等约束。

## 通过标准

### 每个 case 通过标准

1. classify 文种正确
2. extract 不新增事实
3. extract 保留 source_text
4. plan 结构符合文种
5. plan blocked_items 合理
6. draft markdown_draft 可读
7. draft 不新增事实
8. draft 有 fact_usage_report
9. review 能发现预设问题
10. rewrite 能修复 review 指出的问题
11. final_markdown 不保留 critical 问题
12. 所有阶段 JSON 均通过 `jsonschema.validate`
13. manual_confirmation_fields 不得丢失

### 整体通过标准

1. 10 个 case 文件齐全
2. TESTING_GUIDE.md 完成
3. expected/README.md 完成
4. README.md 有测试说明入口
5. 未修改 prompts、schemas、references
6. 未影响旧系统

## 不通过时如何处理

当测试不通过时：

1. **先记录问题** — 将不通过的详细信息记录到 `tests/reports/` 目录
2. **分析原因** — 判断是以下哪种情况：
   - Prompt 逻辑缺陷（应修正 Prompt）
   - 测试样例预期不合理（应修正测试样例）
   - LLM 随机性导致的不稳定输出（应调整预期或增加重试）
3. **再决定是否改 Prompt** — 不要为了通过测试盲目修改 Prompt
4. **优先修正测试样例** — 如果测试预期本身有问题，先改测试
5. **记录修改决策** — 在 reports/ 中记录修改了什么、为什么修改

## 重要规则

### 不得为了通过测试修改 Prompt

测试是验证工具，不是目标。如果测试暴露了真实问题，应该修正 Prompt 或 Schema，但要记录原因。如果只是测试预期不合理，应该修正测试。

### 必须先记录问题，再决定是否改 Prompt

任何 Prompt 修改前，必须在 `tests/reports/` 中记录：
- 哪个 case 失败了
- 失败的具体表现
- 初步分析原因
- 是否需要修改 Prompt
- 修改什么内容
- 修改原因

## 目录结构

```
tests/
├── TESTING_GUIDE.md          # 本文件
├── cases/                     # 测试用例（10 个）
│   ├── 001-news.md
│   ├── 002-fake-report-real-request.md
│   ├── 003-report.md
│   ├── 004-notice.md
│   ├── 005-meeting-minutes.md
│   ├── 006-leader-speech.md
│   ├── 007-summary.md
│   ├── 008-letter.md
│   ├── 009-rag-pollution.md
│   └── 010-terminology-risk.md
├── expected/                  # 预期输出（阶段 12 逐步填充）
│   └── README.md
└── reports/                   # 实际运行报告
    └── README.md
```

## 注意事项

1. 测试样例中的用户初稿故意保留口语化、缺失、模糊，模拟真实场景
2. 预期结果不是"完美输出"，而是"合规输出"——有缺失用占位符是正确的
3. 009（RAG 污染）和 010（称谓风险）是高风险场景，重点验证约束而非质量
4. 所有阶段输出必须通过 jsonschema.validate，不能只用 json.load
5. 如果测试失败，应先记录问题到 reports/，再分析是否需要改 Prompt
