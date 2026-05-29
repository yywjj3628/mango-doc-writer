# mango-doc-writer

## 概述

湖南芒果系文案生产统一入口 Skill。

负责将用户提供的素材/初稿，按照芒果系官方文风生成规范成稿。支持新闻稿、公文（通知/请示/报告/函/通报）、汇报材料、领导讲话、总结、会议纪要等文种。

**阶段 17 已完成 OpenClaw Skill 入口固化，可直接在 OpenClaw 对话中调用。**

## 触发条件

以下情况激活本 Skill：

- 用户要求生成/改写/润色公文、新闻稿、汇报材料、总结、讲话稿等
- 用户提到"芒果风格"、"芒果系"、"官方文稿"、"广电体系"等关键词
- 用户要求按公文规范撰写材料
- 用户要求将素材整理为正式成稿
- 用户要求写请示、报告、通知、函、通报、领导讲话、会议纪要
- 用户要求将初稿优化为芒果系风格

### 不触发条件

- 普通聊天
- 与广电/芒果/公文/新闻稿无关的写作
- 用户只要求翻译
- 用户只要求排版
- 用户只要求摘要但不要求文案生成
- 需要法律、医疗、金融专业意见的内容

## OpenClaw 调用流程

```
用户对话输入
  → OpenClaw 识别触发条件
  → 构造 JSON 输入（或直接传自然语言）
  → 调用 scripts/run_input.py
  → pipeline.run_pipeline()
    → classify → extract → plan → draft(RAG) → review → rewrite
  → output_formatter 格式化结果
  → 返回 final_markdown + 待确认项 + 风险提示
```

### 调用方式

**方式一：结构化 JSON 输入**
```bash
python scripts/run_input.py inputs/example.json
```

**方式二：stdin 管道**
```bash
echo '{"requirement":"请写成新闻稿","draft":"素材内容"}' | python scripts/run_input.py --stdin
```

**方式三：从命令行直接运行**
```bash
python scripts/run_input.py inputs/example.json --stdout --output-dir outputs/custom
```

### 输入格式

```json
{
  "requirement": "用户文案需求",
  "draft": "用户初稿或素材",
  "specified_doc_type": "用户指定文种，可为空",
  "target_unit": "主送单位，可为空",
  "scene": "使用场景，可为空",
  "output_formats": ["markdown"]
}
```

### 输出内容（默认展示）

✅ **展示**：
- final_markdown（主输出）
- manual_confirmation_fields（待确认项）
- remaining_risks（剩余风险）
- output_files（文件路径）
- pipeline_report 摘要（doc_type、rag_status、fallback_count）

❌ **不展示**（除非用户要求调试）：
- classify_result / extract_result / plan_result 全量 JSON
- draft_result / review_result / rewrite_result 全量 JSON
- sanitizer_report 全量 JSON

### 失败处理

如果 pipeline 失败，应展示：
- failed_stage（失败阶段）
- error_type（错误类型）
- error_message（错误描述）
- debug_output_path（如有）
- 建议处理方式

### 输出格式策略

| 文种 | 默认输出 | 可选 DOCX |
|------|---------|----------|
| 新闻稿 | Markdown | — |
| 通知 | Markdown | ✅ |
| 请示 | Markdown | ✅ |
| 报告 | Markdown | ✅ |
| 函 | Markdown | ✅ |
| 通报 | Markdown | ✅ |
| 总结 | Markdown | — |
| 汇报材料 | Markdown | — |
| 领导讲话 | Markdown | — |
| 会议纪要 | Markdown | — |

用户明确要求 DOCX 时才调用 typeset-engine。

### 风险提示策略

- **manual_confirmation_fields 非空** → 必须显示【待确认】列表
- **remaining_risks 非空** → 必须显示【剩余风险】列表
- **sanitizer_high_risk=true** → 必须显示"⚠️ 建议人工复核"

## 核心流程

```
用户初稿 + 文种需求
 → 01-classify：识别文种、行文方向、风险等级
 → 02-extract：抽取事实字段（只抽取用户提供的，不补充）
 → 03-plan：生成文案结构提纲
 → 04-draft：生成初稿（调用 VPS style_rag）
 → 05-review：质检
 → 06-rewrite：二次修订
 → final_markdown
```

## 三类知识分层

| 层 | 文件 | 职责 |
|---|---|------|
| rules_db | `references/doc-type-rules.md` | 公文规则库：能不能这么写 |
| facts_db | `references/org-title-dictionary.yaml` | 称谓口径库：应该怎么称呼 |
| style_rag | RAG（collection: mango_style_docs） | 风格案例库：写得像不像芒果系 |

**优先级：rules_db > facts_db > 用户素材 > style_rag**

## 支持文种

| 文种 | 行文方向 | 风格强度 |
|------|---------|---------|
| 新闻稿 | 对外宣传 | 3 |
| 通知 | 下行文 | 1 |
| 请示 | 上行文 | 1 |
| 报告 | 上行文 | 2 |
| 函 | 平行文 | 1 |
| 总结 | 内部材料 | 2 |
| 汇报材料 | 上行文 | 2 |
| 领导讲话 | 内部材料 | 2-3 |
| 会议纪要 | 内部材料 | 1 |
| 通报 | 下行文 | 1 |

## 强制规则

### 必须

1. **先识别文种，再生成** — 不跳过 classify
2. **加载称谓口径库** — 机构全称、领导职务必须来自 facts_db
3. **使用 RAG 作为风格参考** — 但只借鉴表达方式，不照抄事实
4. **生成后质检** — 不跳过 review
5. **默认输出 Markdown** — 不强制 DOCX/PDF/PPTX
6. **只使用用户提供的事实** — 不得凭空新增数据、荣誉、领导评价

### 禁止

1. ❌ 凭空新增事实、数据、荣誉、领导评价
2. ❌ 报告中夹带请示事项（"请批准""请批复"）
3. ❌ 请示一文多事
4. ❌ 使用禁用称谓（如"湖南卫视总部""芒果总部"）
5. ❌ 将所有文种写成芒果日志新闻稿
6. ❌ RAG 结果中的领导职务/事实直接进入新稿
7. ❌ 缺失领导职务时自行补全（应标记【需人工确认】）
8. ❌ 在 prompt 中散落写死称谓

## 文件结构

```
skills/mango-doc-writer/
├── SKILL.md                          # 本文件
├── README.md                          # 项目说明
├── deploy/                            # VPS 部署
│   ├── check_env.py
│   ├── healthcheck.py
│   ├── run_single.sh
│   ├── run_regression.sh
│   └── systemd/
├── entry/                             # OpenClaw 入口
│   ├── README.md
│   ├── openclaw_entry.md
│   └── input_template.json
├── pipeline/                          # 核心管线
│   ├── run_pipeline.py
│   ├── model_client.py
│   ├── input_parser.py
│   ├── output_formatter.py
│   └── ...
├── scripts/
│   ├── run_case.py
│   ├── run_input.py
│   └── run_all_cases.py
├── prompts/                           # 六阶段提示词
├── schemas/                           # Schema 定义
├── references/                        # 规则库/称谓库
├── tests/                             # 测试与回归
└── docs/                              # 文档
    ├── mango-doc-writer-vps-deployment.md
    └── mango-doc-writer-openclaw-skill-guide.md
```

## 开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| 1-14 | Skill 骨架 → 系统冻结 | ✅ 完成 |
| 15 | DeepSeek API 自动化 | ✅ 完成 |
| 15.2A | flash 模型 + pro fallback | ✅ 完成 |
| 15.2 | 全量 10 case API 回归 | ✅ 完成 |
| 15.3 | 回归规则修正 | ✅ 完成 |
| 16 | VPS 固化部署 | ✅ 完成 |
| 17 | OpenClaw Skill 入口固化 | ✅ 完成 |

---

*最后更新：2026-05-28 (阶段 17)*
