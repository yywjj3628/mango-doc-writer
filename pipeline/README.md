# mango-doc-writer Pipeline

## 目的

最小可运行的六阶段调用入口，串联 classify → extract → plan → draft → review → rewrite，并对每一阶段输出执行 JSON Schema 校验。

**Pipeline 不改 Prompt、不改 Schema、不改 RAG。** Pipeline 只负责串联、校验、保存报告。

## 六阶段调用顺序

```
用户输入 (requirement + draft)
  │
  ├─ 1. classify → classify_result  ──┐
  │   schema: classify.schema.json    │
  ├─ 2. extract → extract_result    │ jsonschema.validate
  │   schema: extract.schema.json    │
  ├─ 3. plan → plan_result          │ 每阶段必须通过
  │   schema: plan.schema.json       │
  ├─ 4. draft → draft_result        │
  │   schema: draft.schema.json      │
  ├─ 5. review → review_result      │
  │   schema: review.schema.json     │
  ├─ 6. rewrite → rewrite_result    ─┘
  │   schema: rewrite.schema.json
  │
  ▼
final_markdown + pipeline_report
```

## 输入格式

```python
from pipeline.run_pipeline import PipelineInput

input_data = PipelineInput(
    requirement="请写一份报告，向集团汇报项目情况。",
    draft="目前项目已完成前期筹备……",
    specified_doc_type="报告",  # 可选
    target_unit="集团",          # 可选
)
```

## 输出格式

```python
from pipeline.run_pipeline import run_pipeline

result = run_pipeline(input_data)

# result.status: "success" | "failed" | "skipped"
# result.final_markdown: 最终 Markdown 正文
# result.pipeline_report: PipelineReport 对象
# result.partial_results: {"classify": {...}, "extract": {...}, ...}
# result.failed_stage: 失败的阶段名称（如 "draft"）
# result.error: 错误信息
```

## Schema 校验机制

所有阶段输出必须通过 `jsonschema.validate` 校验，不能只用 `json.load`。

- 校验由 `schema_loader.validate_result(stage, result)` 执行
- 使用 `schemas/` 目录下的 JSON Schema 文件
- 校验失败会抛出包含 stage 和 schema_path 的 ValidationError
- Pipeline 捕获校验失败，停止后续阶段，返回错误报告

## 错误处理机制

| 状态 | 触发条件 | 返回内容 |
|------|---------|---------|
| `success` | 六阶段全部通过 | final_markdown + pipeline_report |
| `failed` | 某阶段失败 | failed_stage + error + partial_results |
| `skipped` | 模型调用器未接入 | error_type + error_message |

失败时的 error_type：

- `invalid_json` — 模型输出无法解析为 JSON
- `schema_validation_error` — Schema 校验失败
- `stage_error` — 模型调用异常
- `model_runner_not_connected` — 模型调用器未接入

## 如何运行单个 case

```bash
cd skills/mango-doc-writer

python scripts/run_case.py tests/cases/002-fake-report-real-request.md
```

输出目录：

```
tests/reports/002-fake-report-real-request/
├── classify_result.json
├── extract_result.json
├── plan_result.json
├── draft_result.json
├── review_result.json
├── rewrite_result.json
├── pipeline_report.json
└── final_markdown.md
```

## 如何运行全部 case

```bash
cd skills/mango-doc-writer

python scripts/run_all_cases.py
```

输出：

- 每个独立的 case 报告目录
- `tests/reports/summary.json` 汇总文件

## 当前限制

1. **模型调用器未接入** — `call_stage()` 为占位适配器，运行时会返回 `skipped` 状态
2. **接入方式** — 替换 `pipeline/run_pipeline.py` 中的 `call_stage()` 函数，或设置 `MODEL_RUNNER_CONNECTED = True` 并实现调用逻辑
3. **不处理 DOCX/PDF/PPTX** — Pipeline 只输出 Markdown
4. **不提供 Web UI** — Pipeline 是 Python 函数/脚本，不是服务

## 后续如何接入 OpenClaw 模型调用器

在 `pipeline/run_pipeline.py` 中：

1. 设置 `MODEL_RUNNER_CONNECTED = True`
2. 修改 `call_stage(stage_name, payload)` 函数：
   - 根据 stage_name 选择对应 prompt（01-classify.md ~ 06-rewrite.md）
   - 加载 references（doc-type-rules.md、org-title-dictionary.yaml、style-rag-policy.md）
   - 调用 OpenClaw 的模型 API
   - 解析输出为 dict
3. 可选调用 RAG（style_rag）在 plan 和 draft 之间

## 文件结构

```
pipeline/
├── README.md              # 本文件
├── run_pipeline.py         # Pipeline 核心逻辑（DeepSeek API 版本）
├── model_client.py         # DeepSeek API 模型调用客户端
├── rag_client.py           # VPS style_rag 检索客户端
├── schema_loader.py        # Schema 加载与 jsonschema.validate 校验
└── pipeline_types.py       # 类型定义与常量
```

## DeepSeek API 自动化

### 环境变量配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
```

或直接设置环境变量：

```bash
export DEEPSEEK_API_KEY=your_key_here
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-v4-pro
```

### 单 case 运行

```bash
cd skills/mango-doc-writer
python scripts/run_case.py tests/cases/002-fake-report-real-request.md
```

### 全量 case 运行

```bash
python scripts/run_all_cases.py
```

### VPS RAG 调用

draft 阶段自动调用 VPS 上已部署的 RAG 系统（localhost:8000）获取风格参考。
- RAG 失败不阻塞 pipeline
- RAG 只用于风格，不作为事实来源
- pipeline_report 记录 rag_status 和 style_references_count

### 常见错误排查

**invalid_json**
- 原因：模型输出无法解析为 JSON
- 排查：检查 `tests/reports/debug/<stage>-raw-output.txt`
- 解决：重试即可，通常是模型临时异常

**schema_validation_error**
- 原因：JSON 格式正确但不符合 schema
- 排查：检查错误信息中的 path 和 message
- 解决：通常是模型未遵循 schema 约束，重试可能修复

**RAG 失败**
- 原因：localhost:8000 不可达或返回错误
- 排查：`curl -s http://localhost:8000/health`
- 解决：RAG 失败不阻塞 pipeline，draft 阶段继续执行（无风格参考）

**RAG 多 Collection 路由（v0.1.2）**
- `mango_style_docs`: 芒果系风格库，新闻稿/活动稿/领导讲话优先使用
- `jiuyou_docs`: 企业公文库，汇报材料/公文类优先使用
- `openclaw_memory`: 禁止参与 mango-doc-writer RAG
- 配置：通过环境变量 `RAG_COLLECTION_STYLE` / `RAG_COLLECTION_BUSINESS` 控制
- 查看路由表：`pipeline/rag_client.py` → `ROUTING_TABLE`
- pipeline_report.json 记录实际使用的 collections

**missing_api_key**
- 原因：未设置 DEEPSEEK_API_KEY 环境变量
- 解决：创建 .env 文件或 export 环境变量
