# Stage 16 — VPS 固化部署报告

## 执行时间
2026-05-28 16:51–17:00 UTC

## 1. 新增文件清单

| 文件 | 状态 |
|------|------|
| deploy/README.md | ✅ 新增 |
| deploy/env.example | ✅ 新增 |
| deploy/check_env.py | ✅ 新增 |
| deploy/healthcheck.py | ✅ 新增 |
| deploy/run_regression.sh | ✅ 新增 |
| deploy/run_single.sh | ✅ 新增 |
| deploy/logrotate.example | ✅ 新增 |
| deploy/systemd/mango-doc-writer-regression.service | ✅ 新增 |
| deploy/systemd/mango-doc-writer-regression.timer | ✅ 新增 |
| docs/mango-doc-writer-vps-deployment.md | ✅ 新增 |
| scripts/run_input.py | ✅ 新增 |
| logs/.gitkeep | ✅ 新增 |
| outputs/.gitkeep | ✅ 新增 |

## 2. 修改文件清单

| 文件 | 改动 |
|------|------|
| README.md | 增加 VPS 部署文档链接 |
| .gitignore | 增加 .env、logs、debug、outputs 忽略规则 |

## 3. 验证结果

### check_env
**✅ pass** — 17/17 检查通过
- Python 3.10.12
- openai/jsonschema/requests/pyyaml 已安装
- DEEPSEEK_API_KEY 已配置
- 目录结构完整
- reports/outputs/logs 可写
- RAG 可达（localhost:8000）
- typeset-engine 可达（localhost:9090）

### healthcheck
**✅ ok** — 全部服务正常
- DeepSeek API: ok（key 验证通过）
- RAG: ok
- typeset-engine: ok
- 目录可写

### run_single (002-fake-report-real-request)
**✅ success** — 127.9s
- 文种: 请示
- 模型: deepseek-v4-flash
- RAG: success, 6 refs
- 日志: logs/run_single-20260528-165258.log

### run_regression
**✅ 10/10 ALL PASS**
- HR sanitizer: 5 fixes in 5 cases（全部 body_rewritten）

## 4. API Key 安全
- logs/ 中 grep API key → **0 匹配**
- tests/reports/ 中 grep API key → **0 匹配**
- outputs/ 中 grep API key → **0 匹配**
- .gitignore 已忽略 .env

## 5. 日志生成
- `logs/run_single-20260528-165258.log` — 单 case 运行日志

## 6. 是否修改 prompts/schemas/references
**❌ 未修改**

## 7. 是否影响原系统
**❌ 无影响** — 仅新增部署文件，未修改任何业务逻辑

## 8. 建议
**✅ 建议进入 OpenClaw Skill 入口固化**

VPS 部署形态已就绪：
- 环境检查和健康检查脚本可用
- 单篇和回归运行脚本可用
- systemd 定时任务配置已准备
- 日志轮转配置已准备
- 真实输入入口（run_input.py）已就绪

---
*报告生成时间: 2026-05-28 17:00 UTC*
