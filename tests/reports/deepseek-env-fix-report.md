# DeepSeek API Key 环境变量持久化修复报告

> **执行时间**: 2026-05-29 02:40 UTC
> **阶段**: 环境变量修复（非业务逻辑修改）

---

## 1. 失败原因

Pipeline 在 classify 阶段报错：
```
error_type: stage_error
failed_stage: classify
error_message: OSError: 未检测到 DEEPSEEK_API_KEY 环境变量
```

根因：`DEEPSEEK_API_KEY` 只存在于 OpenClaw Gateway 进程环境中，
未持久化到文件系统。当 exec shell 直接运行脚本时，无法继承该变量。

## 2. .env.example 状态

✅ 已更新，包含 DeepSeek + RAG 全部配置项。

## 3. .env 状态

✅ 已创建，包含真实 `DEEPSEEK_API_KEY`。
- 权限: `chmod 600`
- Key 状态: present (len=35)
- **不得提交 Git**

## 4. .gitignore 状态

✅ 已确认包含 `.env` 和 `*.env`。

## 5. run_single.sh env 加载

✅ 已更新，加载优先级：
1. `/etc/mango-doc-writer.env`（系统级）
2. `.env`（项目级）
3. 都不存在则继续运行（check_env 报 missing）

## 6. run_regression.sh env 加载

✅ 同 run_single.sh 逻辑。

## 7. check_env 结果

✅ 全部通过（status: pass, 21/21 checks ok）

## 8. healthcheck 结果

✅ 全部通过（status: ok）

## 9. 002 是否跑通

⚠️ **六阶段全部执行成功（116.5s），但保存阶段报 Python bug**：
```
NameError: name 'final_markdown' is not defined
```

这是阶段 19.3 重构 `run_pipeline.py` 时引入的 bug：
`rewrite_result.get("final_markdown")` 的提取赋值在重构中被遗漏。
已临时修复（添加 `final_markdown = rewrite_result.get("final_markdown", "")`）。

**注意：此修复属于重构 bug fix，非业务逻辑变更。**

## 10. API Key 泄漏检查

✅ 无泄漏：
- .env 文件权限 600
- .gitignore 已排除
- check_env 只输出 present/missing + len
- 本报告不含真实 Key
- run_single.sh 通过 set -a 加载，不在日志中打印

## 11. 修改范围确认

| 文件 | 修改类型 | 是否业务逻辑 |
|------|---------|------------|
| `.env` | 新建（环境配置） | ❌ |
| `.env.example` | 更新 RAG 变量 | ❌ |
| `.gitignore` | 追加 `*.env` | ❌ |
| `deploy/run_single.sh` | env 加载逻辑 | ❌ |
| `deploy/run_regression.sh` | env 加载逻辑 | ❌ |
| `deploy/check_env.py` | key 检查增强 + 去重 | ❌ |
| `pipeline/run_pipeline.py` | 修复 final_markdown 未定义 bug | ⚠️ 重构 bug fix |

**prompts / schemas / references / RAG 路由 / pipeline 业务逻辑：未修改。**

---

*报告时间: 2026-05-29 02:42 UTC*
