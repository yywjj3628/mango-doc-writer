# Mango Doc Writer — VPS 部署文档

## 1. 部署目标

将六阶段 DeepSeek API 自动化公文写作管线固化为 VPS 上可运行、可维护、可回归测试的部署形态。

## 2. 当前架构

```
用户输入 (JSON/Markdown)
    ↓
classify → extract → plan → draft → review → rewrite
    ↓                              ↑
    └─── style_rag (VPS RAG) ─────┘
    ↓
final_markdown.md (主输出)
final.docx (可选，需 typeset-engine)
```

**模型策略**：
- 默认：deepseek-v4-flash（低成本）
- 兜底：deepseek-v4-pro（失败时自动 fallback）

## 3. 环境变量

复制模板并填入真实值：

```bash
cp deploy/env.example .env
vim .env
```

| 变量 | 必需 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | ❌ | 默认 https://api.deepseek.com |
| `DEEPSEEK_MODEL` | ❌ | 默认 deepseek-v4-flash |
| `DEEPSEEK_FALLBACK_MODEL` | ❌ | 默认 deepseek-v4-pro |
| `RAG_ENABLED` | ❌ | 默认 true |
| `TYPESET_ENGINE_ENABLED` | ❌ | 默认 true |

**注意**：`.env` 不得提交 Git，API key 不得写入日志/报告。

## 4. 安装依赖

```bash
pip install openai jsonschema requests
# 可选
pip install pyyaml
```

## 5. 检查环境

```bash
python3 deploy/check_env.py
```

输出 JSON 格式的检查结果。关键项失败时退出码为 2。

## 6. 健康检查

```bash
python3 deploy/healthcheck.py
```

轻量检查，验证 API key 有效、RAG/typeset-engine 可达、目录可写。不消耗 API token。

## 7. 运行单个 case

```bash
bash deploy/run_single.sh tests/cases/002-fake-report-real-request.md
```

## 8. 运行真实输入

### 方式一：Shell 脚本

```bash
bash deploy/run_single.sh inputs/example.json
```

### 方式二：直接调用 Python

```bash
python3 scripts/run_input.py inputs/example.json
```

### 输入 JSON 格式

```json
{
  "requirement": "请写成芒果系新闻稿",
  "draft": "用户初稿内容",
  "specified_doc_type": null,
  "target_unit": null,
  "scene": null,
  "output_formats": ["markdown"]
}
```

### 输出

输出目录：`outputs/<timestamp>/`

包含：classify_result.json、extract_result.json、plan_result.json、draft_result.json、review_result.json、rewrite_result.json、final_markdown.md、pipeline_report.json、sanitizer_report.json（如有）

## 9. 运行全量回归

```bash
bash deploy/run_regression.sh
```

执行 10 case 全量回归 + schema 校验 + markdown claims 检查。

日志输出到 `logs/regression-<timestamp>.log`

返回码：0=全部通过，1=存在失败，2=环境错误

## 10. 查看输出

```bash
# 最新输出
ls -lt outputs/

# 查看最终文档
cat outputs/<timestamp>/final_markdown.md

# 查看报告
cat tests/reports/<case_id>/pipeline_report.json
```

## 11. 查看日志

```bash
# 最新日志
ls -lt logs/

# 回归日志
cat logs/regression-<timestamp>.log

# Debug 文件（schema 校验失败时生成）
ls tests/reports/debug/
```

## 12. 配置 systemd 定时回归

```bash
# 安装
sudo cp deploy/systemd/mango-doc-writer-regression.service /etc/systemd/system/
sudo cp deploy/systemd/mango-doc-writer-regression.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mango-doc-writer-regression.timer

# 查看状态
sudo systemctl list-timers mango-doc-writer-regression.timer

# 手动触发
sudo systemctl start mango-doc-writer-regression.service

# 查看日志
sudo journalctl -u mango-doc-writer-regression.service -f
```

默认：每周一凌晨 3:00 运行。

## 13. 日志轮转

```bash
sudo cp deploy/logrotate.example /etc/logrotate.d/mango-doc-writer
```

保留策略：回归日志 30 天，debug 文件 7 天。

## 14. 常见错误处理

### missing_api_key
```
错误: 未检测到 DEEPSEEK_API_KEY 环境变量
处理: 检查 .env 文件是否存在，API key 是否正确
```

### invalid_json
```
错误: 模型输出无法解析为 JSON
处理: 系统自动重试 DEEPSEEK_MAX_RETRIES 次；仍失败则查看 tests/reports/debug/ 下的原始输出
```

### schema_validation_error
```
错误: Schema 校验失败
处理: sanitizer 自动修复常见问题（enum、null、missing required）；仍失败则 fallback 到 deepseek-v4-pro
```

### RAG unavailable
```
警告: RAG 服务不可达
处理: draft 阶段跳过 RAG 风格参考，pipeline 继续；pipeline_report 记录 rag_status=failed
```

### typeset-engine unavailable
```
警告: typeset-engine 不可达
处理: DOCX 生成跳过，Markdown 输出不受影响
```

### sanitizer high-risk
```
警告: sanitizer high-risk sanitizer_high_risk=true
处理: 查看 sanitizer_report.json 了解修复详情（如 body_rewritten 强制修正）；不影响最终文档质量
```

## 15. 不建议开放 Web API

当前形态为 VPS 上的命令行工具，不建议直接暴露 Web API。如需对外服务，应通过 OpenClaw Skill 入口间接调用。

## 16. OpenClaw Skill 入口

后续可通过 OpenClaw SKILL.md 集成：

1. OpenClaw 接收用户需求（飞书/Telegram）
2. 构造 JSON 输入
3. 调用 `scripts/run_input.py`
4. 将 final_markdown 返回给用户
5. 可选：调用 typeset-engine 生成 DOCX 并发送文件

具体集成方式待后续阶段设计。

---

## 17. mango_style_docs 语料库（阶段 19.2）

### 概述

`mango_style_docs` 是专为 `style_rag` 风格参考新建的高质量芒果系文案语料库，替代原 `hunan_mango`（仅60条概述级摘要）。

### Collection 信息

| 字段 | 值 |
|------|-----|
| collection 名称 | `mango_style_docs` |
| points_count | 148 |
| vector_size | 1024 |
| distance | Cosine |
| embedding 模型 | BAAI/bge-m3 |
| 来源 | 飞书多维表格（芒果日志） |
| 文章数 | 60 |
| 文种覆盖 | 新闻稿/领导讲话/活动稿/党建材料/通报 |

### 环境变量

```bash
RAG_COLLECTION_MANGO_STYLE=mango_style_docs
```

### 与 hunan_mango 对比

| 维度 | mango_style_docs | hunan_mango |
|---|---|---|
| chunk 数 | 148 | 60 |
| doc_type 覆盖 | 100% | 10% |
| category 覆盖 | 100% | 0% |
| is_fact_safe 覆盖 | 100% | 0% |
| 按段落切分 | ✅ | ❌ |
| 审计评分 | 85/100 | 68/100 |

### 目录结构

```
corpus/mango_style_docs/
├── cleaned/           # 60 篇标准 Markdown
├── manifest.yaml      # 语料清单
└── README.md
```

### 脚本

- `scripts/ingest_mango_style_docs.py` — 自定义 ingest 脚本（Docker 容器内执行）
- `scripts/audit_mango_style_docs.py` — 审计脚本（待完善）

---

*文档版本: 阶段 19.2 | 2026-05-29*
